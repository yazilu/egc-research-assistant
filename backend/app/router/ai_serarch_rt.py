from fastapi import APIRouter, Body, UploadFile, File, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
import uuid
from schemas.chat import ChatRequest
from fastapi.responses import StreamingResponse
import json
import os
import re
from dotenv import load_dotenv
from typing import List, Optional
from openai import OpenAI
from sqlalchemy import text
from service.core.file_parse import execute_insert_process
from service.core.api.utils.file_utils import get_project_base_directory
from service.core.text_extraction import extract_text, validate_supported_extension
from database.knowledgebase_operations import get_chat_history
from service.core.retrieval import retrieve_content
from service.core.chat import get_chat_completion
from utils import logger
from database.knowledgebase_operations import insert_knowledgebase, verify_user_knowledgebase
from database.egc_operations import update_extraction_status
from service.web_search.procss_web_search import store_and_query_snippets
from service.agent.agent import final_answer
from utils.prompt import DirectAnswerPrompt
from utils.database import get_db

# 加载 .env 文件
load_dotenv()

router = APIRouter()

# 简单对话无需检索的关键词（快速预判，避免不必要的 LLM 调用）
SKIP_RETRIEVAL_PATTERNS = [
    '你好', '谢谢', '再见', '早上好', '晚上好', '下午好',
    '你是谁', '你能做什么', '介绍一下', 'hello', 'hi', 'thanks',
    '好的', '嗯', '哦', '明白了', '知道了', '可以',
]


def needs_retrieval(message: str) -> bool:
    """
    判断用户消息是否需要检索文档/网络。

    先用规则预判明显不需要检索的消息；无法确定时用轻量 LLM 分类。
    """
    msg = message.strip().lower()

    # 1. 规则预判：极短消息或纯寒暄 → 无需检索
    if len(msg) <= 2:
        return False

    for pattern in SKIP_RETRIEVAL_PATTERNS:
        if msg == pattern.lower():
            return False

    # 2. 含明显 EGC 相关术语 → 需要检索（快速路径，不调 LLM）
    egc_keywords = [
        'egc', 'ecc', '地聚合物', '偏高岭土', '粉煤灰', '矿渣',
        'pva', 'pe纤维', 'pp纤维', '钢纤维', '玄武岩纤维',
        '抗压强度', '抗拉强度', '拉伸应变', '抗折强度', '弹性模量',
        '水胶比', '砂胶比', '碱激发', '养护', '纤维掺量',
        '应变硬化', '多缝开裂', '自愈合', '氯离子', '碳化',
        '配合比', '配比', '力学性能', '纤维桥接',
        'geopolymer', 'fly ash', 'slag', 'metakaolin',
        'tensile strain', 'compressive strength', 'flexural',
        'strain hardening', 'fiber bridging',
    ]
    for kw in egc_keywords:
        if kw in msg:
            return True

    # 3. 无法判断 → 轻量 LLM 分类
    try:
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        completion = client.chat.completions.create(
            model="qwen2.5-72b-instruct",
            messages=[{
                "role": "user",
                "content": (
                    '判断以下用户消息是否与EGC（高延性地聚合物复合材料）'
                    '研究相关。EGC相关包括：材料配比、力学性能、纤维增强、'
                    '养护条件、微观机理、耐久性等。\n\n'
                    f'用户消息：{message}\n\n'
                    '请只返回一个JSON：{"is_egc_related": true} 或 '
                    '{"is_egc_related": false}'
                ),
            }],
            response_format={"type": "json_object"},
            stream=False,
        )
        content = completion.choices[0].message.content
        result = json.loads(content)
        return result.get("is_egc_related", True)
    except Exception as e:
        logger.warning(f"意图分类失败，默认检索: {e}")
        return True


MAX_ATTACHMENT_CHARS = 30000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
SAFE_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _safe_upload_filename(file: UploadFile) -> str:
    file_name = os.path.basename((file.filename or "").replace("\\", "/"))
    if not file_name or file_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return file_name


async def _read_upload_content(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File size cannot exceed 20 MB")
    return content


def _safe_storage_subdirectory(session_id: str) -> str:
    if not SAFE_SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id")
    return session_id


def build_question_with_attachments(message: str, attachments: list[str]) -> str:
    """将附件文本拼入用户问题，超过长度限制则截断"""
    if not attachments:
        return message

    parts = []
    for i, text in enumerate(attachments):
        if len(text) > MAX_ATTACHMENT_CHARS:
            text = text[:MAX_ATTACHMENT_CHARS] + f"\n\n[文档过长，仅截取前{MAX_ATTACHMENT_CHARS}字符]"
        parts.append(f"### 附件文档 {i + 1}\n{text}")

    doc_section = "\n\n".join(parts)
    truncated_note = ""
    if any(len(a) > MAX_ATTACHMENT_CHARS for a in attachments):
        truncated_note = f"\n注意：文档内容较长，仅截取了前{MAX_ATTACHMENT_CHARS}字符进行分析。"

    return (
        f"## 用户上传的文档\n\n{doc_section}\n\n"
        f"---\n\n"
        f"## 用户问题\n{message}"
        f"{truncated_note}"
    )



def _format_chat_history(history: list[dict]) -> str:
    """将对话历史格式化为 Q&A 文本，供 prompt 使用"""
    if not history:
        return "（无历史对话）"

    lines = []
    for i, turn in enumerate(history, 1):
        lines.append(f"Q{i}: {turn['question']}")
        lines.append(f"A{i}: {turn['answer']}")
    return "\n".join(lines)


def _format_kb_reference_for_prompt(ref: dict) -> str:
    return (
        "来源类型: 本地知识库\n"
        f"标题: {ref.get('document_name', '未知文档')}\n"
        f"内容: {ref.get('content_with_weight', '')}"
    )


def _format_web_reference_for_prompt(ref: dict) -> str:
    metadata = []
    if ref.get("source"):
        metadata.append(f"检索源: {ref.get('source')}")
    if ref.get("year"):
        metadata.append(f"年份: {ref.get('year')}")
    if ref.get("doi"):
        metadata.append(f"DOI: {ref.get('doi')}")
    if ref.get("url"):
        metadata.append(f"URL: {ref.get('url')}")
    metadata_text = "\n".join(metadata)
    if metadata_text:
        metadata_text += "\n"
    return (
        "来源类型: 网络/学术检索\n"
        f"标题: {ref.get('title', '网页')}\n"
        f"{metadata_text}"
        f"摘要: {ref.get('content', '')}"
    )


##################################
# 创建一个新的对话 Session
##################################

@router.post("/create_session")
async def create_session(
    payload: Optional[dict] = Body(default=None),
    # credentials: JwtAuthorizationCredentials = Security(access_security),
):
    try:
        user_id = "1"
        # user_id = credentials.subject.get("user_id")
        # if not user_id:
        #     raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        session_id = str(uuid.uuid4()).replace("-", "")[:16]
        session_name = str((payload or {}).get("session_name") or "新对话")[:255]

        db = next(get_db())
        try:
            db.execute(
                text(
                    """
                    INSERT INTO sessions (session_id, user_id, session_name)
                    VALUES (:session_id, :user_id, :session_name)
                    """
                ),
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "session_name": session_name,
                },
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        return {
            "session_id": session_id,
            "status": "success",
            "message": "Session created successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/upload_chat_file/")
async def upload_chat_file(
    files: List[UploadFile] = File(...),
):
    """上传对话附件：根据文件类型选用对应解析器提取文本"""
    try:
        results = []
        for file in files:
            file_name = _safe_upload_filename(file)
            ext = validate_supported_extension(file_name)

            # 保存到临时文件（使用 uuid 避免并发冲突）
            tmp_dir = os.path.join(get_project_base_directory(), "storage/tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}{ext}")
            with open(tmp_path, "wb") as buffer:
                buffer.write(await _read_upload_content(file))

            try:
                text_content = await run_in_threadpool(_extract_text, tmp_path, ext)
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            if not text_content.strip():
                logger.warning(f"文件 {file_name} 提取文本为空，可能是扫描件或无法解析的格式")

            results.append({
                "file_name": file_name,
                "text_content": text_content,
            })

        return {
            "status": "success",
            "message": "文件解析成功",
            "files": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def _extract_text(file_path: str, ext: str) -> str:
    """根据文件扩展名选用合适的解析器提取纯文本"""
    return extract_text(file_path, ext)


@router.post("/upload_files/")
async def upload_files(
    session_id: Optional[str] = Query(None),
    files: List[UploadFile] = File(...),
    # credentials: JwtAuthorizationCredentials = Security(access_security),
):
    if session_id is None:
        session_id = "default"  # 设置默认值
    session_id = _safe_storage_subdirectory(session_id)
    # 确保 storage/file 文件夹存在
    storage_dir = os.path.join(get_project_base_directory(), "storage/file")
    os.makedirs(storage_dir, exist_ok=True)

    # 根据 session_id 创建子文件夹
    session_dir = os.path.join(storage_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        user_id = "1"

        for file in files:
            file_name = _safe_upload_filename(file)
            validate_supported_extension(file_name)
            file_path = os.path.join(session_dir, file_name)

            # 保存文件到本地
            with open(file_path, "wb") as buffer:
                buffer.write(await _read_upload_content(file))

            kb_id = await run_in_threadpool(insert_knowledgebase, user_id, file_name)
            logger.info("Created knowledgebase record id=%s for %s", kb_id, file_name)

            try:
                await run_in_threadpool(execute_insert_process, file_path, file_name, user_id, kb_id)
                logger.info("Indexed knowledgebase document id=%s", kb_id)
            except Exception:
                await run_in_threadpool(update_extraction_status, kb_id, "failed")
                raise

        return {
            "status": "success",
            "message": "文件解析成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

##################################
# ai搜索
##################################

@router.post("/ai_search/")
async def ai_search(
    session_id: str = Query(...),
    request: ChatRequest = Body(..., description="User message"),
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    # db: Session = Depends(get_db),
):
    try:
        user_id = '1'

        question = request.message

        # 判断是否需要检索：附件、用户显式开启本地搜索/网络搜索时才进入参考资料链路。
        wants_references = bool(request.attachments) or request.local_search or request.web_search
        should_search = False
        if wants_references:
            should_search = bool(request.attachments) or await run_in_threadpool(needs_retrieval, question)

        kb_references = []
        kb_contents = []
        top_snippets = []
        related_questions = []
        web_contents = []

        if should_search:
            # --- 检索路径 ---
            if request.local_search:
                has_knowledgebase = await run_in_threadpool(verify_user_knowledgebase, user_id)

                if has_knowledgebase:
                    kb_references = await run_in_threadpool(retrieve_content, user_id, request.message)
                    logger.info("Knowledgebase retrieval returned %s chunks", len(kb_references))
                else:
                    logger.info("知识库未找到相关查询结果")
            else:
                logger.info("Local search disabled for this chat request")

            kb_contents = [ref['content_with_weight'] for ref in kb_references]

            if request.web_search:
                try:
                    top_snippets, related_questions = await run_in_threadpool(
                        store_and_query_snippets, request.message
                    )
                    web_contents = [item["content"] for item in top_snippets]
                    logger.info(f"网络搜索完成: {len(top_snippets)} 条结果, {len(related_questions)} 个相关问题")
                except Exception as e:
                    logger.warning(f"网络搜索失败，将在无网络参考下继续: {e}")
                    top_snippets = []
                    related_questions = []
                    web_contents = []
        else:
            logger.info("Skipped retrieval for a non-EGC chat message")

        # 历史上下文
        chat_history = await run_in_threadpool(get_chat_history, session_id)
        logger.info("Loaded %s chat history turns", len(chat_history))

        # prompt 参考内容：附件（首要） + 知识库 + 网络搜索。
        # 顺序必须与前端展示来源一致：附件 -> 本地知识库 -> 网络/学术检索。
        final_reference = [
            _format_kb_reference_for_prompt(ref) for ref in kb_references
        ] + [
            _format_web_reference_for_prompt(ref) for ref in top_snippets
        ]
        if request.attachments:
            doc_only = build_question_with_attachments("", request.attachments)
            doc_only = doc_only.replace("\n\n---\n\n## 用户问题\n", "")
            final_reference = [f"[用户上传的文档 — 首要参考]\n{doc_only}"] + final_reference

        if should_search:
            formatted_refs = "\n\n---\n\n".join(
                f"### 参考来源 {i+1}\n引用标记: ##{i}$$\n{ref}" for i, ref in enumerate(final_reference)
            ) if final_reference else "（无参考内容）"

            formatted_history = _format_chat_history(chat_history)

            # INITIAL_QUERY 只放用户问题，文档内容仅在 {0} Search results 中出现一次
            final_prompt = DirectAnswerPrompt.format(formatted_refs, formatted_history, question)
        else:
            # 直接回答，使用简化 prompt；本地搜索/网络搜索关闭时不强行检索。
            formatted_history = _format_chat_history(chat_history)
            final_prompt = (
                "你是一个EGC（高延性地聚合物复合材料）研究助手。"
                "请根据已有专业知识和历史对话，友好、准确、简洁地回答。"
                "如果用户的问题需要最新资料或本地文献依据，请提示其开启网络搜索或本地搜索。\n\n"
                f"## 历史对话\n{formatted_history}\n\n"
                f"## 用户问题\n{question}"
            )

        logger.info(
            "Prepared chat response: retrieval=%s local_search=%s web_search=%s attachments=%s prompt_chars=%s",
            should_search,
            request.local_search,
            request.web_search,
            len(request.attachments),
            len(final_prompt),
        )

        # 返回流式响应
        return StreamingResponse(
            get_chat_completion(session_id, question, kb_references, user_id, final_prompt, related_questions, top_snippets, request.web_search, request.attachments),
            media_type="text/event-stream"
        )


    except HTTPException as e:
        # 捕获 HTTPException 并重新抛出，保持状态码和详情
        raise e
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/deep_research/")
async def deep_research(
    session_id: str = Query(...),
    request: ChatRequest = Body(..., description="User message"),
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    # db: Session = Depends(get_db),
):
    try:
        user_id = '1'
        question = build_question_with_attachments(request.message, request.attachments)
        logger.info(
            "Prepared deep research request: attachments=%s web_search=%s prompt_chars=%s",
            len(request.attachments),
            request.web_search,
            len(question),
        )
        # 返回流式响应
        return StreamingResponse(
            final_answer(question, session_id, user_id, request.web_search, request.attachments),
            media_type="text/event-stream"
        )


    except HTTPException as e:
        # 捕获 HTTPException 并重新抛出，保持状态码和详情
        raise e
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
