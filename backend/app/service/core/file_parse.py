import xxhash
import datetime
import logging
import os
import re
import unicodedata

from service.core.rag.app.manual import chunk as deepdoc_chunk
from service.core.rag.nlp import naive_merge
from service.core.rag.utils.es_conn import ESConnection
from service.core.rag.nlp.model import generate_embedding
from service.core.text_extraction import extract_pdf_index_text, extract_text, get_file_extension

logger = logging.getLogger(__name__)


def dummy(prog=None, msg=""):
    pass


class ChunkProcessingError(RuntimeError):
    pass


class EmbeddingGenerationError(RuntimeError):
    pass


def _build_doc_metadata(file_path: str) -> dict:
    title = re.sub(r"\.[a-zA-Z0-9]+$", "", os.path.basename(file_path))
    title_tks = _simple_tokenize(title)
    return {
        "docnm_kwd": file_path,
        "title_tks": title_tks,
        "title_sm_tks": _simple_tokenize(title, include_unigrams=True),
    }


def _simple_tokenize(text: str, include_unigrams: bool = False) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    tokens = []
    for segment in re.findall(r"[\u4e00-\u9fff]+|[a-z0-9][a-z0-9._%+\-/]*", normalized):
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            if len(segment) == 1:
                tokens.append(segment)
            else:
                tokens.extend(segment[i:i + 2] for i in range(len(segment) - 1))
            if include_unigrams:
                tokens.extend(segment)
        else:
            tokens.append(segment)
    return " ".join(tokens)


def _text_to_documents(file_path: str, text: str) -> list[dict]:
    sections = [(line.strip(), "") for line in text.splitlines() if line.strip()]
    if not sections:
        return []

    doc = _build_doc_metadata(file_path)
    chunks = naive_merge(sections, 256, "\n!?。；！？")
    documents = []
    for chunk_text in chunks:
        if not chunk_text.strip():
            continue
        item = dict(doc)
        item["content_with_weight"] = chunk_text
        item["content_ltks"] = _simple_tokenize(chunk_text)
        item["content_sm_ltks"] = _simple_tokenize(chunk_text, include_unigrams=True)
        documents.append(item)
    return documents



def _parse_pdf(file_path: str) -> list[dict]:
    parse_mode = os.getenv("PDF_PARSE_MODE", "fast").lower()
    if parse_mode == "deepdoc":
        logger.info("Parsing PDF with DeepDOC because PDF_PARSE_MODE=deepdoc: %s", file_path)
        return deepdoc_chunk(file_path, callback=dummy)

    try:
        text = extract_pdf_index_text(file_path)
        if text.strip():
            documents = _text_to_documents(file_path, text)
            logger.info(
                "Parsed PDF with pypdf fast path: path=%s chars=%s chunks=%s",
                file_path,
                len(text),
                len(documents),
            )
            if documents:
                return documents
    except Exception as exc:
        logger.warning("Fast PDF parse failed for %s; falling back to DeepDOC: %s", file_path, exc)

    if os.getenv("PDF_DEEPDOC_FALLBACK", "1") == "0":
        logger.warning("Fast PDF parse produced no chunks and DeepDOC fallback is disabled: %s", file_path)
        return []

    logger.info("Falling back to DeepDOC PDF parser: %s", file_path)
    return deepdoc_chunk(file_path, callback=dummy)


def parse(file_path):
    ext = get_file_extension(file_path)
    if ext == ".pdf":
        return _parse_pdf(file_path)

    text = extract_text(file_path, ext)
    documents = _text_to_documents(file_path, text)
    logger.info(
        "Parsed file with text extractor: path=%s ext=%s chars=%s chunks=%s",
        file_path,
        ext,
        len(text),
        len(documents),
    )
    return documents



def process_item(item, file_name, session_id):
    """
    处理单条数据
    """
    required_fields = ["content_with_weight", "content_ltks", "content_sm_ltks", "docnm_kwd", "title_tks"]
    missing_fields = [field for field in required_fields if field not in item]
    if missing_fields:
        raise ChunkProcessingError(f"Parsed chunk is missing fields: {', '.join(missing_fields)}")

    content = item["content_with_weight"]
    if not content or not content.strip():
        raise ChunkProcessingError("Parsed chunk content is empty")

    # 生成 chunk_id
    chunck_id = xxhash.xxh64((content + session_id).encode("utf-8")).hexdigest()

    # 构建数据字典
    d = {
        "id": chunck_id,
        "content_ltks": item["content_ltks"],
        "content_with_weight": content,
        "content_sm_ltks": item["content_sm_ltks"],
        "important_kwd": [],
        "important_tks": [],
        "question_kwd": [],
        "question_tks": [],
        "create_time": str(datetime.datetime.now()).replace("T", " ")[:19],
        "create_timestamp_flt": datetime.datetime.now().timestamp()
    }

    d["kb_id"] = session_id
    d["docnm_kwd"] = item["docnm_kwd"]
    d["title_tks"] = item["title_tks"]
    d["doc_id"] = xxhash.xxh64(file_name.encode("utf-8")).hexdigest()
    d["docnm"] = file_name

    v = generate_embedding(content)
    if not v:
        raise EmbeddingGenerationError(
            f"Embedding API returned no vector for {file_name}; check DASHSCOPE_API_KEY and network access"
        )

    # 将嵌入向量存储到字典中
    d["q_%d_vec" % len(v)] = v

    return d

def execute_insert_process(file_path, file_name, session_id, kb_id=None):
    """
    执行文档处理和插入 Elasticsearch 的函数
    :param file_path: 文件路径
    :param session_id: 会话 ID
    :param documents: 要插入的文档列表
    """
    logger.info("Start parsing knowledgebase file: file_name=%s path=%s", file_name, file_path)
    documents = parse(file_path)
    logger.info("Finished parsing knowledgebase file: file_name=%s chunks=%s", file_name, len(documents))

    result = []
    processing_errors = []
    for index, item in enumerate(documents):
        try:
            processed_item = process_item(item, file_name, session_id)
            result.append(processed_item)
        except EmbeddingGenerationError:
            logger.exception("Embedding generation failed for %s at chunk %s", file_name, index)
            raise
        except Exception as e:
            processing_errors.append(f"chunk {index}: {e}")
            logger.exception("Failed to prepare document chunk for %s at chunk %s: %s", file_name, index, e)

    if not result:
        detail = "; ".join(processing_errors[:3]) if processing_errors else "parser returned no usable text"
        raise RuntimeError(f"No searchable chunks were generated for {file_name}: {detail}")

    if processing_errors:
        logger.warning(
            "Skipped %s malformed chunks for %s; first errors: %s",
            len(processing_errors),
            file_name,
            "; ".join(processing_errors[:3]),
        )

    # 创建 ESConnection 的实例
    es_connection = ESConnection()
    # 通过实例调用 insert 方法
    insert_errors = es_connection.insert(documents=result, indexName=session_id)
    if insert_errors:
        raise RuntimeError(f"Failed to index {file_name}: {'; '.join(insert_errors)}")
    logger.info("Inserted %s chunks into Elasticsearch index %s for %s", len(result), session_id, file_name)

    # EGC 论文元数据提取（异步触发，不阻塞上传响应）
    try:
        from database.knowledgebase_operations import get_kb_id_by_filename
        from database.egc_operations import update_extraction_status, update_paper_metadata, bulk_insert_experimental_data
        from service.core.egc_extraction import extract_paper_metadata, extract_experimental_data, normalize_experimental_data
        import threading

        def _run_extraction():
            try:
                resolved_kb_id = kb_id or get_kb_id_by_filename(file_name, session_id)
                if not resolved_kb_id:
                    logger.warning("Could not find kb_id for %s; skipping extraction", file_name)
                    return

                update_extraction_status(resolved_kb_id, "processing")

                # 提取论文元数据
                metadata = extract_paper_metadata(documents)
                if metadata:
                    update_paper_metadata(resolved_kb_id, metadata)

                # 提取实验数据
                raw_data = extract_experimental_data(documents)
                if raw_data:
                    normalized = normalize_experimental_data(raw_data)
                    for item in normalized:
                        item['kb_id'] = resolved_kb_id
                        item['file_name'] = file_name
                        item['user_id'] = session_id
                    bulk_insert_experimental_data(normalized)

                update_extraction_status(resolved_kb_id, "completed")
                logger.info("EGC metadata extraction completed for %s", file_name)
            except Exception as e:
                logger.exception("EGC extraction failed for %s: %s", file_name, e)
                try:
                    resolved_kb_id = kb_id or get_kb_id_by_filename(file_name, session_id)
                    if resolved_kb_id:
                        update_extraction_status(resolved_kb_id, "failed")
                except Exception:
                    logger.exception("Failed to mark extraction failure for %s", file_name)

        threading.Thread(target=_run_extraction, daemon=True).start()
    except ImportError as e:
        logger.warning("EGC extraction module not available: %s", e)
    except Exception as e:
        logger.exception("Could not schedule EGC extraction for %s: %s", file_name, e)



import json
import os

if __name__ == "__main__":
    file_path = "/mnt/d/wsl/project/gsk-poc/storage/file/【兴证电子】世运电路2023中报点评.pdf"
    session_id = "40e2743ccffa4207"
    output_file = "/mnt/d/wsl/project/gsk-poc/storage/output/result.json"

    # 如果本地文件不存在，则解析文件并保存结果
    if not os.path.exists(output_file):
        documents = parse(file_path)
        
        # 处理每个文档
        result = []
        for item in documents:
            processed_item = process_item(item, file_path, session_id)
            result.append(processed_item)

        # 将结果保存到本地文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)  # 确保目录存在
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"结果已保存到本地文件: {output_file}")
    else:
        # 如果本地文件存在，则从文件中读取结果
        with open(output_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        print(f"从本地文件加载结果: {output_file}")

    # # 打印结果以便检查
    # print("加载的数据内容：")
    # print(json.dumps(result, ensure_ascii=False, indent=4))

    # 创建 ESConnection 的实例
    es_connection = ESConnection()
    # 通过实例调用 insert 方法
    es_connection.insert(documents=result, indexName="世运电路2023中报点评")
