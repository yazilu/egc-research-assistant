from service.core.retrieval import retrieve_content
from utils import logger
import json
from openai import OpenAI
import os
import re


MIN_DEEP_LOCAL_REFERENCES = 6
MIN_DEEP_WEB_REFERENCES = 10
MIN_DEEP_LOCAL_PAPERS = 6
MIN_DEEP_WEB_PAPERS = 10
DEEP_REFERENCE_BLOCK_CHARS = 1600
CITATION_PATTERN = re.compile(r"##(\d+)\$\$")
WEB_ACADEMIC_SOURCES = {"openalex", "crossref", "semantic scholar"}

WEB_SEARCH_QUERY_HINTS = [
    "最新",
    "近期",
    "近年",
    "现在",
    "当前",
    "进展",
    "动态",
    "趋势",
    "网络",
    "互联网",
    "搜索",
    "文献",
    "论文",
    "综述",
    "latest",
    "recent",
    "current",
    "new",
    "trend",
    "web",
    "internet",
    "search",
    "literature",
    "paper",
    "papers",
    "publication",
    "publications",
    "review",
]


def _query_needs_web_search(query: str) -> bool:
    text = (query or "").lower()
    return any(hint in text for hint in WEB_SEARCH_QUERY_HINTS)


def _is_trivial_query(query: str) -> bool:
    text = (query or "").strip().lower()
    if len(text) <= 2:
        return True
    return text in {"你好", "您好", "hello", "hi", "谢谢", "thanks", "好的", "嗯", "哦"}


def _build_deep_web_search_prompt(query: str) -> str:
    return (
        f"{query} EGC ECC UHPC SHCC UHPFRC "
        "engineered geopolymer composites engineered cementitious composites "
        "academic literature web sources"
    )


def _build_deep_local_search_prompt(query: str) -> str:
    return (
        f"{query} EGC ECC UHPC SHCC UHPFRC "
        "engineered geopolymer composites mechanical properties experimental data "
        "mix design fiber bridging strain hardening"
    )


def _normalize_action_name(action_name: str) -> str:
    name = str(action_name or "").strip()
    compact = re.sub(r"\s+", "", name).lower()

    if "文档" in name or "附件" in name or compact in {"documentanalysis", "docanalysis"}:
        return "文档分析"
    if "预测" in name or "性能" in name or compact in {"prediction", "predict", "performanceprediction"}:
        return "性能预测"
    if (
        "网络" in name
        or "联网" in name
        or "互联网" in name
        or compact in {"websearch", "internetsearch", "online_search", "searchweb"}
    ):
        return "网络搜索"
    if (
        "论文" in name
        or "学术" in name
        or "文献" in name
        or "检索" in name
        or compact in {"rag", "academicsearch", "literatureretrieval"}
    ):
        return "学术论文检索"
    return name or "学术论文检索"


def _ensure_web_search_action(actions: list[dict], query: str, web_search: bool) -> list[dict]:
    normalized_actions = []
    has_web_action = False

    for action in actions:
        if not isinstance(action, dict):
            continue
        normalized = dict(action)
        normalized["action_name"] = _normalize_action_name(normalized.get("action_name", ""))
        if normalized["action_name"] == "网络搜索":
            has_web_action = True
        normalized_actions.append(normalized)

    if web_search and not has_web_action and not _is_trivial_query(query):
        normalized_actions.append({
            "action_name": "网络搜索",
            "prompt": _build_deep_web_search_prompt(query),
        })
        logger.info("Added required web search action for deep research because web search is enabled")

    return normalized_actions


def _ensure_local_search_action(actions: list[dict], query: str) -> list[dict]:
    normalized_actions = []
    has_local_action = False

    for action in actions:
        if not isinstance(action, dict):
            continue
        normalized = dict(action)
        normalized["action_name"] = _normalize_action_name(normalized.get("action_name", ""))
        if normalized["action_name"] == "学术论文检索":
            has_local_action = True
        normalized_actions.append(normalized)

    if not has_local_action and not _is_trivial_query(query):
        normalized_actions.append({
            "action_name": "学术论文检索",
            "prompt": _build_deep_local_search_prompt(query),
        })
        logger.info("Added required local literature action for deep research")

    return normalized_actions


def extract_json_content(input_str):
    """
    提取字符串中第一个"["和最后一个"]"之间的内容（包括中括号）

    Args:
        input_str (str): 需要处理的输入字符串

    Returns:
        str or None: 提取的JSON内容，如果没有匹配则返回None
    """
    pattern = r'(\[[\s\S]*\])'
    match = re.search(pattern, input_str)

    return match.group(1) if match else None


def middle_json_model(prompt):
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': prompt}],
        response_format={"type": "json_object"}
    )
    return completion.choices[0].message.content


# ============================================================
# RAG 学术论文检索
# ============================================================

def rag(query):
    indexNames = "1"
    rag_results = retrieve_content(indexNames, query, page_size=12, top_k=80)
    return rag_results


# ============================================================
# 网络搜索
# ============================================================

def web_search_answer(query):
    try:
        from service.web_search.academic_search import deduplicate_snippets, search_academic_literature
        from service.web_search.web_search import serper_search, process_search_results

        academic_snippets = []
        web_snippets = []

        try:
            academic_snippets = search_academic_literature(query, limit=36)
        except Exception as e:
            logger.warning("Academic search failed: %s", e)

        try:
            search_results = serper_search(query, num=30)
            web_snippets, related_questions = process_search_results(search_results, original_query=query)
        except Exception as e:
            logger.warning("Serper search failed: %s", e)

        snippets = deduplicate_snippets([*academic_snippets, *web_snippets])
        if snippets:
            return snippets
        return "网络搜索暂时不可用，未从学术源或普通网页源获取到结果"
    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return f"网络搜索暂时不可用，错误信息: {str(e)}"


# ============================================================
# Plan 模块：分析用户查询，决定使用哪些工具
# ============================================================

def agent_plan(query, web_search=False):
    # 网络搜索可用性提示
    web_search_constraint = ""
    if not web_search:
        web_search_constraint = """
**重要：用户已关闭网络搜索功能。禁止使用"网络搜索"工具，仅可使用"学术论文检索"、
"性能预测"和"文档分析"。**
"""
    else:
        web_search_constraint = """
**重要：用户已开启网络搜索功能。除非是简单问候或完全不需要检索的问题，
计划中必须至少包含一个"网络搜索"工具，用于补充公开网页、最新论文摘要、
出版社页面、DOI页面或开放获取资料。**
"""

    prompt = '''
    # EGC力学性能研究助手的Plan模块

你是一个专业的EGC（Engineered Geopolymer Composites，高延性地聚合物复合材料）
力学性能研究助手的规划模块。你的任务是：
1. 分析用户关于EGC材料力学性能的查询：{0}
2. 基于已有的信息，决定使用哪个工具来查询以获得更多需要的信息
3. 将用户的原始查询拆解或延伸为2-4个相关问题，以获取更全面的信息

{1}

## 可用工具
1. **学术论文检索**：搜索本地EGC/ECC论文库，可检索以下领域：
   - 材料配比（粉煤灰、矿渣、偏高岭土掺量、水胶比、砂胶比、碱激发剂类型与模数）
   - 纤维特性（PVA、PE、PP、钢纤维、玄武岩纤维的类型、掺量、长度、直径）
   - 力学性能（抗压强度、极限拉伸应变、抗折强度、弹性模量、抗拉强度）
   - 养护条件对性能的影响（温度、龄期、养护方式）
   - 微观结构与性能关系（纤维桥接、基体-纤维界面、应变硬化行为）
   - 耐久性（氯离子渗透、碳化、抗冻融）
   - 不同基体体系对比（粉煤灰基 vs 矿渣基 vs 复合基）
   - 配合比优化方法

2. **网络搜索**：在互联网上搜索最新的EGC研究进展、学术论文摘要、会议报告

3. **性能预测**：基于已有实验数据，预测给定配比的力学性能

4. **文档分析**：用户上传了PDF文档（查询中以"## 用户上传的文档"标记），
   需要从文档中提取EGC相关的材料配比、力学性能、实验数据等信息。
   此工具不需要外部搜索，直接基于文档内容进行分析。

## 工具选择规则
- **重要**：如果用户查询中包含"## 用户上传的文档"标记，说明用户提供了文档，
  必须使用**文档分析**作为第一个action，提取文档中的EGC相关数据
- 对于文档分析，prompts 应包含从文档中提取的具体问题，如：
  "从文档中提取EGC材料配比信息"、"从文档中提取力学性能实验数据"等
- 文档分析后，可以使用**学术论文检索**或**网络搜索**补充对比数据
- 查询具体材料配比、力学性能数据、实验现象解释时，优先使用**学术论文检索**
- 查询最新研究进展、综述、行业动态时，使用**网络搜索**
- 用户给出具体配比询问"预测性能"或"能获得多少强度"时，使用**性能预测**
- 网络搜索的prompt需增加"EGC"、"engineered geopolymer composite"、
  "mechanical properties"等关键词

## 输出格式
你的输出应该是一个JSON格式的列表，每个项目包含：
1. `action_name`：工具名称（"学术论文检索"、"网络搜索"、"性能预测"、"文档分析"）
2. `prompts`：问题列表，第一个是原始查询，后面是拆解或延伸的问题
[
  {{
    "action_name": "工具名称",
    "prompts": [
      "原始查询",
      "拆解/延伸问题1",
      "拆解/延伸问题2"
    ]
  }}
]

## 示例

### 示例1：关于纤维对性能影响的查询
用户：PVA纤维掺量对EGC极限拉伸应变有什么影响？

输出：
[
  {{
    "action_name": "学术论文检索",
    "prompts": [
      "PVA纤维掺量对EGC极限拉伸应变有什么影响？",
      "不同PVA纤维体积掺量下EGC的应变硬化行为",
      "PVA纤维与基体界面结合对拉伸应变的影响机制"
    ]
  }}
]

### 示例2：关于不同体系的对比查询
用户：粉煤灰基EGC和矿渣基EGC在力学性能上有什么差异？

输出：
[
  {{
    "action_name": "学术论文检索",
    "prompts": [
      "粉煤灰基EGC的力学性能特征",
      "矿渣基EGC的抗压强度和拉伸应变对比"
    ]
  }},
  {{
    "action_name": "网络搜索",
    "prompts": [
      "fly ash vs slag based EGC mechanical properties comparison recent research",
      "geopolymer composite binder type effect on strain hardening 2024 2025"
    ]
  }}
]

### 示例3：关于配比预测的查询
用户：水胶比0.30、PVA纤维2%、常温养护28天的EGC抗压强度大概多少？

输出：
[
  {{
    "action_name": "性能预测",
    "prompts": [
      "水胶比0.30、PVA纤维2%、常温养护28天的EGC抗压强度预测"
    ]
  }},
  {{
    "action_name": "学术论文检索",
    "prompts": [
      "水胶比0.30 PVA纤维2% EGC 28天抗压强度实验数据"
    ]
  }}
]

### 示例4：用户上传文档进行查询
用户：## 用户上传的文档
### 附件文档 1
[文档内容包含EGC实验配比和力学性能数据...]
---
## 用户问题
这份文档中EGC的抗压强度是多少？

输出：
[
  {{
    "action_name": "文档分析",
    "prompts": [
      "从文档中提取EGC材料配比和力学性能数据",
      "提取文档中所有抗压强度相关实验数据"
    ]
  }},
  {{
    "action_name": "学术论文检索",
    "prompts": [
      "类似EGC配比的文献抗压强度对比数据"
    ]
  }}
]

### 示例5：简单问候
用户：你好
这种情况下都不需要调用工具，则输出为None

只需要输出JSON的部分，前后不要输出任何信息

    '''.format(query, web_search_constraint)
    result = (middle_json_model(prompt))
    logger.debug("Agent planning response received (%s characters)", len(result or ""))
    json_list = extract_json_content(result)
    try:
        structure_output = json.loads(json_list)
    except (TypeError, json.JSONDecodeError):
        structure_output = None

    return structure_output


# ============================================================
# 状态调整：将多 prompt 的 action 展开为单 prompt 的列表
# ============================================================

def adjust_format(original_data):
    """
    调整数据格式，使每个action_name只搭配一个prompt

    参数:
    original_data (list): 原始数据，可能是结构化 dict 列表或简单字符串列表

    返回:
    list: 调整后的数据，每个action_name只对应一个prompt
    """
    adjusted_data = []

    for item in original_data:
        # 容错：模型可能返回简单字符串而非结构化 dict
        if isinstance(item, str):
            adjusted_data.append({
                'action_name': '文档分析' if '文档' in item else '学术论文检索',
                'prompt': item,
            })
            continue
        if not isinstance(item, dict):
            continue

        action_name = _normalize_action_name(item.get('action_name', '学术论文检索'))
        prompts = item.get('prompts', item.get('prompt', []))

        # 容错：prompts 可能是字符串
        if isinstance(prompts, str):
            prompts = [prompts]
        if not isinstance(prompts, list):
            prompts = [str(prompts)]

        for prompt in prompts:
            adjusted_data.append({
                'action_name': action_name,
                'prompt': prompt,
            })

    return adjusted_data


# ============================================================
# Reflect 模块：检查已有信息是否足够，决定是否继续检索
# ============================================================

def reflection(user_query, memory_global, web_search=False):
    has_doc = "## 用户上传的文档" in user_query
    doc_note = ""
    if has_doc:
        doc_note = """
注意：用户已上传PDF文档。文档内容已在查询中提供。反思时应考虑：
- 文档中是否缺少关键数据（如提到配比但无具体数值）
- 是否需要从文献库中查找对比数据来验证文档中的结论
- 若文档已被截断，可考虑是否需要针对文档提及的关键词进行补充检索
"""
    web_note = ""
    if not web_search:
        web_note = "\n注意：用户已关闭网络搜索，你只能使用学术论文检索。\n"

    prompt = '''
    你是一个专业的EGC力学性能研究助手的反思模块。你的任务是：
1. 分析用户的查询: {0}
2. 基于已有的信息，判断是否还需要延伸查询以获得更全面的配比-性能数据
{2}
{3}

##目前已有的信息:
{1}

## 可用工具
1. **学术论文检索**：搜索本地EGC/ECC论文库，可检索以下领域：
   - 材料配比（粉煤灰、矿渣、偏高岭土掺量、水胶比、砂胶比、碱激发剂类型与模数）
   - 纤维特性（PVA、PE、PP、钢纤维、玄武岩纤维的类型、掺量、长度、直径）
   - 力学性能（抗压强度、极限拉伸应变、抗折强度、弹性模量、抗拉强度）
   - 养护条件对性能的影响（温度、龄期、养护方式）
   - 微观结构与性能关系（纤维桥接、基体-纤维界面、应变硬化行为）
   - 耐久性（氯离子渗透、碳化、抗冻融）
   - 不同基体体系对比（粉煤灰基 vs 矿渣基 vs 复合基）
   - 配合比优化方法

2. **网络搜索**：在互联网上搜索最新的EGC研究进展

## 工具选择规则
- 查询具体材料配比、力学性能数据时，优先使用**学术论文检索**
- 查询最新研究进展时，使用**网络搜索**
- 网络检索的查询扩展侧重于本地无法检索到的最新信息

## 反思判断规则
- 如果已获取的数据涵盖了用户关心的配比范围（如水胶比 ±0.05、
  纤维掺量 ±1%），则不需要继续检索
- 如果缺少关键力学性能数据（如只有抗压强度而没有拉伸应变），
  则需要补充检索
- 如果缺少特定纤维类型的对比数据，则需要补充检索

###重要！
至多再扩展不超过4个查询，如果需要扩展则按照下面的输出格式输出，
如果不需要则返回None

## 输出格式
你的输出应该是一个JSON格式的列表，每个项目包含：
1. `action_name`：工具名称（"学术论文检索"或"网络搜索"）
2. `prompts`：一个扩展的问题，检索内容一定是一个简单明确的问题
[
  {{
    "action_name": "工具名称",
    "prompts": "查询内容"
  }}
  ...
]

    '''.format(user_query, memory_global, doc_note, web_note)
    result = (middle_json_model(prompt))
    json_list = extract_json_content(result)
    try:
        structure_output = json.loads(json_list)
    except (TypeError, json.JSONDecodeError):
        structure_output = None

    return structure_output


# ============================================================
# 去重模块
# ============================================================

def deduplicate_memory_global(memory):
    """
    对最终的memory进行全局去重，根据所有结果中的content_with_weight字段去重

    Args:
        memory: 记忆列表，每个元素包含"提问"和"结果"字段

    Returns:
        deduplicated_memory: 去重后的记忆列表
    """
    if not isinstance(memory, list):
        return memory

    seen_content = set()
    deduplicated_memory = []

    for memory_item in memory:
        if not isinstance(memory_item, dict) or '结果' not in memory_item:
            deduplicated_memory.append(memory_item)
            continue

        result = memory_item['结果']

        if isinstance(result, list):
            deduplicated_result = []
            for item in result:
                if isinstance(item, dict) and 'content_with_weight' in item:
                    content = item['content_with_weight'].strip()
                    content_hash = hash(content)
                    if content_hash not in seen_content:
                        seen_content.add(content_hash)
                        deduplicated_result.append(item)
                    else:
                        logger.debug("Removed duplicate retrieval result id=%s", item.get('id', 'unknown'))
                else:
                    deduplicated_result.append(item)

            new_memory_item = {
                "提问": memory_item['提问'],
                "结果": deduplicated_result
            }
            deduplicated_memory.append(new_memory_item)
        else:
            deduplicated_memory.append(memory_item)

    return deduplicated_memory


# ============================================================
# Execute 模块：依次执行 actions
# ============================================================

def process_actions(actions, web_search=False):
    """
    处理动作列表函数

    Args:
        actions: 动作列表，每个动作包含action_name和prompt
        web_search: 是否允许网络搜索

    Returns:
        memory: 包含每次调用结果的记忆列表
    """
    memory = []

    for action in actions:
        action_name = _normalize_action_name(action.get('action_name', ''))
        prompt = action.get('prompt', '')

        # 硬性检查：网络搜索关闭时直接跳过
        if action_name == '网络搜索' and not web_search:
            logger.info("Skipped web search action because web search is disabled")
            memory_item = {
                "提问": prompt,
                "结果": [{"message": "网络搜索已关闭，未执行"}]
            }
            memory.append(memory_item)
            continue

        logger.info("Executing deep research action: %s", action_name)

        try:
            if action_name == '学术论文检索':
                result = rag(prompt)
            elif action_name == '网络搜索':
                result = web_search_answer(prompt)
            elif action_name == '性能预测':
                # 调用预测服务
                try:
                    from service.core.egc_predictor import predict_from_query
                    result = predict_from_query(prompt)
                except ImportError:
                    result = [{"message": "预测服务暂不可用，请先检索相关论文数据"}]
            elif action_name == '文档分析':
                result = [{
                    "message": "文档内容已随用户查询一起提供，将在最终回答阶段基于文档内容进行分析。"
                }]
            else:
                result = f"未知的动作类型: {action_name}"

            memory_item = {
                "提问": prompt,
                "结果": result
            }
            memory.append(memory_item)

            logger.debug("Deep research action %s produced a result", action_name)

        except Exception as e:
            logger.exception("Deep research action %s failed: %s", action_name, e)
            continue

    logger.info("Completed %s deep research actions", len(memory))

    total_before = sum(len(item['结果']) if isinstance(item['结果'], list) else 1 for item in memory)
    deduplicated_memory = deduplicate_memory_global(memory)
    total_after = sum(len(item['结果']) if isinstance(item['结果'], list) else 1 for item in deduplicated_memory)

    logger.info(
        "Deduplicated deep research results: before=%s after=%s removed=%s",
        total_before,
        total_after,
        total_before - total_after,
    )

    return deduplicated_memory


# ============================================================
# Final Answer：汇总所有检索结果，生成最终回答
# ============================================================

def _strip_doc_for_plan(query: str) -> str:
    """Remove embedded document content from query for fast planning.

    Agent plan / reflection don't need the full document text — they just
    need to know that a document was uploaded (the marker is enough).
    """
    if "## 用户上传的文档" not in query:
        return query
    parts = query.split("\n## 用户问题\n", 1)
    if len(parts) == 2:
        return f"[用户上传了PDF文档，需要分析]\n\n{parts[1]}"
    return query


def _dedupe_kb_refs(refs: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for ref in refs or []:
        if not isinstance(ref, dict):
            continue
        content = str(ref.get("content_with_weight") or "").strip()
        key = (
            "kb",
            str(ref.get("document_id") or ref.get("id") or ""),
            content[:500],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _kb_paper_key(ref: dict) -> str:
    if not isinstance(ref, dict):
        return ""
    document_id = str(ref.get("document_id") or "").strip().lower()
    document_name = str(ref.get("document_name") or "").strip().lower()
    return document_id or document_name


def _distinct_kb_paper_count(refs: list[dict]) -> int:
    return len({key for key in (_kb_paper_key(ref) for ref in refs or []) if key})


def _order_kb_refs_for_paper_diversity(refs: list[dict]) -> list[dict]:
    refs = _dedupe_kb_refs(refs)
    first_by_paper = []
    remaining_by_paper = []
    seen_papers = set()

    for ref in refs:
        paper_key = _kb_paper_key(ref)
        if paper_key and paper_key not in seen_papers:
            seen_papers.add(paper_key)
            first_by_paper.append(ref)
        else:
            remaining_by_paper.append(ref)

    return [*first_by_paper, *remaining_by_paper]


def _normalized_title(value: str) -> str:
    return re.sub(r"\W+", " ", str(value or "").lower()).strip()


def _web_paper_key(ref: dict) -> str:
    if not isinstance(ref, dict):
        return ""
    doi = str(ref.get("doi") or "").strip().lower()
    title = _normalized_title(ref.get("title") or "")
    url = str(ref.get("url") or "").strip().lower()
    return doi or (f"title:{title}" if title else "") or (f"url:{url}" if url else "")


def _is_academic_web_ref(ref: dict) -> bool:
    if not isinstance(ref, dict):
        return False
    source = str(ref.get("source") or "").strip().lower()
    url = str(ref.get("url") or "").strip().lower()
    return (
        bool(ref.get("doi"))
        or source in WEB_ACADEMIC_SOURCES
        or "doi.org" in url
        or "semanticscholar.org" in url
        or "openalex.org" in url
        or "crossref.org" in url
        or "springer.com" in url
        or "sciencedirect.com" in url
        or "elsevier.com" in url
        or "wiley.com" in url
        or "onlinelibrary.wiley.com" in url
        or "tandfonline.com" in url
        or "mdpi.com" in url
        or "ascelibrary.org" in url
        or "nature.com" in url
        or "sagepub.com" in url
        or "frontiersin.org" in url
        or "researchgate.net" in url
    )


def _distinct_web_paper_count(refs: list[dict]) -> int:
    return len({
        key
        for ref in refs or []
        if _is_academic_web_ref(ref)
        for key in [_web_paper_key(ref)]
        if key
    })


def _order_web_refs_for_paper_diversity(refs: list[dict]) -> list[dict]:
    refs = _dedupe_web_refs(refs)
    academic_first = []
    non_academic_first = []
    remaining = []
    seen_papers = set()

    for ref in refs:
        paper_key = _web_paper_key(ref)
        if not paper_key or paper_key in seen_papers:
            remaining.append(ref)
            continue
        seen_papers.add(paper_key)
        if _is_academic_web_ref(ref):
            academic_first.append(ref)
        else:
            non_academic_first.append(ref)

    return [*academic_first, *non_academic_first, *remaining]


def _dedupe_web_refs(refs: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for ref in refs or []:
        if not isinstance(ref, dict):
            continue
        content = str(ref.get("content") or "").strip()
        key = _web_paper_key(ref)
        if not (key or content):
            continue
        key = key or f"content:{content[:300]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _local_top_up_queries(query: str) -> list[str]:
    return [
        _build_deep_local_search_prompt(query),
        f"{query} EGC mix design compressive strength tensile strain flexural strength",
        f"{query} PVA PE fiber volume curing age mechanical properties engineered geopolymer composites",
        f"{query} strain hardening fiber bridging matrix fiber interface experimental results",
        f"{query} fly ash slag metakaolin geopolymer composite mechanical performance",
        f"{query} engineered cementitious composites tensile ductility multiple cracking",
        f"{query} curing temperature age alkali activator modulus geopolymer composite strength",
        f"{query} durability chloride carbonation freeze thaw EGC mechanical properties",
    ]


def _web_top_up_queries(query: str) -> list[str]:
    return [
        _build_deep_web_search_prompt(query),
        f"{query} engineered geopolymer composites recent review DOI 2023 2024 2025 2026",
        f"{query} EGC ECC SHCC UHPFRC mechanical properties OpenAlex Crossref Semantic Scholar",
        f"{query} engineered cementitious composites geopolymer latest journal article conference paper",
        f"{query} engineered geopolymer composites tensile strain compressive strength DOI",
        f"{query} geopolymer engineered cementitious composites PVA fiber journal article",
        f"{query} alkali activated strain hardening cementitious composite review paper",
        f"{query} fly ash slag based engineered geopolymer composites mechanical properties article",
    ]


def _top_up_kb_refs(refs: list[dict], query: str, min_count: int = MIN_DEEP_LOCAL_REFERENCES) -> list[dict]:
    refs = _order_kb_refs_for_paper_diversity(refs)
    target_papers = min(MIN_DEEP_LOCAL_PAPERS, min_count)
    if (
        len(refs) >= min_count
        and _distinct_kb_paper_count(refs) >= target_papers
    ) or _is_trivial_query(query):
        return refs

    for top_up_query in _local_top_up_queries(query):
        if len(refs) >= min_count and _distinct_kb_paper_count(refs) >= target_papers:
            break
        try:
            extra_refs = rag(top_up_query)
        except Exception as exc:
            logger.warning("Deep research local reference top-up failed: %s", exc)
            continue

        if isinstance(extra_refs, list):
            refs = _order_kb_refs_for_paper_diversity([*refs, *extra_refs])

    logger.info(
        "Deep research local references topped up to %s chunks from %s papers",
        len(refs),
        _distinct_kb_paper_count(refs),
    )
    return refs


def _top_up_web_refs(
    refs: list[dict],
    query: str,
    web_search_enabled: bool,
    min_count: int = MIN_DEEP_WEB_REFERENCES,
) -> list[dict]:
    refs = _order_web_refs_for_paper_diversity(refs)
    target_papers = min(MIN_DEEP_WEB_PAPERS, min_count)
    if (
        not web_search_enabled
        or (
            len(refs) >= min_count
            and _distinct_web_paper_count(refs) >= target_papers
        )
        or _is_trivial_query(query)
    ):
        return refs

    for top_up_query in _web_top_up_queries(query):
        if len(refs) >= min_count and _distinct_web_paper_count(refs) >= target_papers:
            break
        extra_refs = web_search_answer(top_up_query)
        if isinstance(extra_refs, list):
            refs = _order_web_refs_for_paper_diversity([*refs, *extra_refs])
        else:
            logger.warning("Deep research web reference top-up returned no usable snippets")

    logger.info(
        "Deep research web references topped up to %s items from %s academic papers",
        len(refs),
        _distinct_web_paper_count(refs),
    )
    return refs


def _format_marker_list(markers: list[int]) -> str:
    return "、".join(f"##{marker}$$" for marker in markers)


def _first_markers_by_kb_paper(local_markers: list[int], local_refs: list[dict]) -> list[int]:
    selected = []
    seen_papers = set()
    for marker, ref in zip(local_markers, local_refs or []):
        paper_key = _kb_paper_key(ref)
        if not paper_key or paper_key in seen_papers:
            continue
        seen_papers.add(paper_key)
        selected.append(marker)
    return selected


def _first_markers_by_web_paper(web_markers: list[int], web_refs: list[dict]) -> list[int]:
    selected = []
    seen_papers = set()
    for marker, ref in zip(web_markers, web_refs or []):
        if not _is_academic_web_ref(ref):
            continue
        paper_key = _web_paper_key(ref)
        if not paper_key or paper_key in seen_papers:
            continue
        seen_papers.add(paper_key)
        selected.append(marker)
    return selected


def _build_citation_quota_instruction(
    local_markers: list[int],
    web_markers: list[int],
    local_refs: list[dict],
    web_refs: list[dict],
    web_search_enabled: bool,
) -> str:
    local_paper_markers = _first_markers_by_kb_paper(local_markers, local_refs)
    web_paper_markers = _first_markers_by_web_paper(web_markers, web_refs)
    local_required = min(MIN_DEEP_LOCAL_REFERENCES, len(local_markers))
    local_papers_required = min(MIN_DEEP_LOCAL_PAPERS, len(local_paper_markers))
    web_required = min(MIN_DEEP_WEB_REFERENCES, len(web_markers))
    web_papers_required = min(MIN_DEEP_WEB_PAPERS, len(web_paper_markers))
    lines = [
        "引用配额要求（非常重要）：",
        "来源面板只展示正文中实际出现过的引用标记，因此下列标记必须出现在正文的关键结论、表格单元或段落句末。",
    ]

    if local_required:
        lines.append(
            f"- 本地知识库：至少使用 {local_required} 个不同引用标记，并优先覆盖 "
            f"{local_papers_required} 篇不同本地论文；不同论文优先标记为："
            f"{_format_marker_list(local_paper_markers[:local_papers_required])}。"
            "同一篇论文的其他片段可以作为补充证据，但不能替代不同论文覆盖。"
        )
    else:
        lines.append("- 本地知识库：本次未检索到可用本地引用，请明确说明本地文献依据不足，不要编造本地引用。")

    if web_search_enabled:
        if web_required:
            lines.append(
                f"- 网络/学术检索：至少使用 {web_required} 个不同引用标记，并优先覆盖 "
                f"{web_papers_required} 篇不同网络学术论文；不同论文优先标记为："
                f"{_format_marker_list(web_paper_markers[:web_papers_required])}。"
                "普通网页可作为补充，但不能替代网络学术论文覆盖。"
            )
        else:
            lines.append("- 网络/学术检索：本次网络检索未返回可用来源，请明确说明网络文献依据不足，不要编造网络引用。")
    else:
        lines.append("- 网络/学术检索：用户未开启网络搜索，本次不要求网络引用。")

    lines.append("如果同一结论同时有本地和网络依据，尽量同时引用本地标记和网络标记。")
    return "\n".join(lines)


def _cited_markers(text: str) -> set[int]:
    markers = set()
    for match in CITATION_PATTERN.finditer(text or ""):
        try:
            markers.add(int(match.group(1)))
        except (TypeError, ValueError):
            continue
    return markers


def _one_line(value: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _build_reference_appendix_line(marker: int, ref: dict, source_label: str) -> str:
    if source_label == "本地文献":
        title = ref.get("document_name") or "本地知识库文献"
        content = ref.get("content_with_weight") or ""
    else:
        title = ref.get("title") or "网络/学术检索文献"
        content = ref.get("content") or ""
    return f"- {source_label}：{_one_line(title, 90)}。{_one_line(content)} ##{marker}$$"


def _build_citation_coverage_appendix(
    answer: str,
    local_markers: list[int],
    web_markers: list[int],
    local_refs: list[dict],
    web_refs: list[dict],
    web_search_enabled: bool,
) -> str:
    cited = _cited_markers(answer)
    local_required = min(MIN_DEEP_LOCAL_REFERENCES, len(local_markers))
    local_paper_markers = _first_markers_by_kb_paper(local_markers, local_refs)
    local_papers_required = min(MIN_DEEP_LOCAL_PAPERS, len(local_paper_markers))
    web_paper_markers = _first_markers_by_web_paper(web_markers, web_refs)
    web_papers_required = min(MIN_DEEP_WEB_PAPERS, len(web_paper_markers)) if web_search_enabled else 0
    web_required = min(MIN_DEEP_WEB_REFERENCES, len(web_markers)) if web_search_enabled else 0

    cited_local_count = len(cited.intersection(local_markers))
    cited_local_papers = {
        _kb_paper_key(ref)
        for marker, ref in zip(local_markers, local_refs or [])
        if marker in cited and _kb_paper_key(ref)
    }
    cited_local_paper_count = len(cited_local_papers)
    cited_web_count = len(cited.intersection(web_markers))
    cited_web_papers = {
        _web_paper_key(ref)
        for marker, ref in zip(web_markers, web_refs or [])
        if marker in cited and _is_academic_web_ref(ref) and _web_paper_key(ref)
    }
    cited_web_paper_count = len(cited_web_papers)
    missing_local_count = max(0, local_required - cited_local_count)
    missing_local_paper_count = max(0, local_papers_required - cited_local_paper_count)
    missing_web_count = max(0, web_required - cited_web_count)
    missing_web_paper_count = max(0, web_papers_required - cited_web_paper_count)

    if (
        missing_local_count == 0
        and missing_local_paper_count == 0
        and missing_web_count == 0
        and missing_web_paper_count == 0
    ):
        return ""

    lines = [
        "\n\n#### 补充文献依据",
        "为保证深度探索的来源覆盖，以下补充列出本次检索中尚未充分出现在正文中的关键来源：",
    ]

    local_lookup = dict(zip(local_markers, local_refs or []))
    web_lookup = dict(zip(web_markers, web_refs or []))

    for marker in local_paper_markers:
        if missing_local_paper_count <= 0:
            break
        if marker in cited:
            continue
        ref = local_lookup.get(marker)
        if not ref:
            continue
        paper_key = _kb_paper_key(ref)
        if paper_key and paper_key in cited_local_papers:
            continue
        lines.append(_build_reference_appendix_line(marker, ref, "本地文献"))
        cited.add(marker)
        if paper_key:
            cited_local_papers.add(paper_key)
        missing_local_count = max(0, missing_local_count - 1)
        missing_local_paper_count -= 1

    for marker in local_markers:
        if missing_local_count <= 0:
            break
        if marker in cited:
            continue
        ref = local_lookup.get(marker)
        if not ref:
            continue
        lines.append(_build_reference_appendix_line(marker, ref, "本地文献"))
        cited.add(marker)
        missing_local_count -= 1

    for marker in web_paper_markers:
        if missing_web_paper_count <= 0:
            break
        if marker in cited:
            continue
        ref = web_lookup.get(marker)
        if not ref:
            continue
        paper_key = _web_paper_key(ref)
        if paper_key and paper_key in cited_web_papers:
            continue
        lines.append(_build_reference_appendix_line(marker, ref, "网络/学术文献"))
        cited.add(marker)
        if paper_key:
            cited_web_papers.add(paper_key)
        missing_web_count = max(0, missing_web_count - 1)
        missing_web_paper_count -= 1

    for marker in web_markers:
        if missing_web_count <= 0:
            break
        if marker in cited:
            continue
        ref = web_lookup.get(marker)
        if not ref:
            continue
        lines.append(_build_reference_appendix_line(marker, ref, "网络/学术文献"))
        cited.add(marker)
        missing_web_count -= 1

    appendix = "\n".join(lines)
    logger.info(
        "Appended citation coverage supplement: local_before=%s/%s local_papers_before=%s/%s web_before=%s/%s web_papers_before=%s/%s chars=%s",
        cited_local_count,
        local_required,
        cited_local_paper_count,
        local_papers_required,
        cited_web_count,
        web_required,
        cited_web_paper_count,
        web_papers_required,
        len(appendix),
    )
    return appendix


def final_answer(user_query, session_id=None, user_id=None, web_search=False, attachments=None):
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False    # 判断是否结束思考过程并开始回复
    completed = False

    # 立即发送状态消息，避免前端空白等待
    yield f"event: message\ndata: {json.dumps({'role': 'agent', 'content': '正在分析问题...'})}\n\n"

    # 计划阶段用精简 query（去掉文档全文），大幅加速 agent_plan
    plan_query = _strip_doc_for_plan(user_query)
    effective_web_search = web_search or _query_needs_web_search(plan_query)
    if effective_web_search and not web_search:
        logger.info("Enabled web search for deep research because the query requests current web information")

    action_tool = agent_plan(plan_query, effective_web_search)
    logger.info(f"action_tool: {action_tool}")

    if action_tool:
        adjusted_tools = adjust_format(action_tool)
        actions = _ensure_local_search_action(
            _ensure_web_search_action(adjusted_tools, plan_query, effective_web_search),
            plan_query,
        )
    else:
        actions = _ensure_local_search_action(
            _ensure_web_search_action([], plan_query, effective_web_search),
            plan_query,
        )

    for action in actions:
        if isinstance(action, dict):
            action_name = action.get('action_name', '')
            prompt = action.get('prompt', '')
            message = {
                "role": "agent",
                "content": f'正在执行{action_name}: "{prompt}"'
            }
            json_message = json.dumps(message)
            yield f"event: message\ndata: {json_message}\n\n"

    memory_new = process_actions(actions, effective_web_search)

    memory_global = []
    memory_global.extend(memory_new)

    # 反思模块
    action_reflect = reflection(plan_query, memory_global, effective_web_search)
    if action_reflect:
        logger.info("回顾内容，进行反思...")
        # 将 reflection 结果展开为统一的 action 格式
        reflect_actions = []
        for item in action_reflect:
            if not isinstance(item, dict):
                continue
            prompts = item.get('prompts', item.get('prompt', ''))
            if isinstance(prompts, str):
                prompts = [prompts]
            elif not isinstance(prompts, list):
                prompts = [str(prompts)]
            for prompt in prompts:
                reflect_actions.append({
                    'action_name': item.get('action_name', ''),
                    'prompt': prompt,
                })
        reflect_actions = _ensure_web_search_action(reflect_actions, plan_query, effective_web_search)
        memory_new = process_actions(reflect_actions, effective_web_search)
        memory_global.extend(memory_new)

    # 从 memory_global 中提取知识库和网络搜索结果，发送给前端展示
    all_kb_refs = []
    all_web_refs = []
    for mem in (memory_global or []):
        if not isinstance(mem, dict):
            continue
        results = mem.get('结果', [])
        if not isinstance(results, list):
            continue
        for item in results:
            if isinstance(item, dict):
                if 'content_with_weight' in item:
                    # ES 知识库检索结果（完整元数据，与 ai_search 路径格式一致）
                    all_kb_refs.append(item)
                elif 'content' in item and ('title' in item or 'url' in item):
                    # 网络搜索结果（保持原始格式，前端 mapper 会从 title/content/url 字段提取）
                    all_web_refs.append(item)

    all_kb_refs = _top_up_kb_refs(all_kb_refs, plan_query)
    all_kb_refs = _order_kb_refs_for_paper_diversity(all_kb_refs)
    all_web_refs = _top_up_web_refs(all_web_refs, plan_query, effective_web_search)
    all_web_refs = _order_web_refs_for_paper_diversity(all_web_refs)

    # 发送用户上传附件引用给前端展示
    if attachments:
        attachment_refs = []
        for i, text in enumerate(attachments):
            attachment_refs.append({
                "document_name": f"用户上传附件 {i + 1}",
                "content_with_weight": text[:300],
                "_source": "attachment",
            })
        yield f"event: message\ndata: {json.dumps({'attachments': attachment_refs})}\n\n"

    if all_kb_refs:
        yield f"event: message\ndata: {json.dumps({'documents': all_kb_refs})}\n\n"
    if all_web_refs:
        yield f"event: message\ndata: {json.dumps({'web_search': all_web_refs})}\n\n"

    has_doc = "## 用户上传的文档" in user_query
    doc_instruction = ""
    if has_doc:
        doc_instruction = """
        重要：用户已上传PDF文档（在"用户问题"中以"## 用户上传的文档"标记）。
        请将文档内容作为**首要信息来源**，仔细提取和分析文档中的EGC相关数据。
        检索结果仅作为补充参考。回答时应明确区分"文档数据"和"文献参考数据"。
        如果文档中包含实验配比表、力学性能表，请以表格形式整理呈现。
        如果文档内容被截断（标注了"文档过长，仅截取前..."），请说明分析范围。
        """

    # 将参考内容格式化为与前端来源列表一致的顺序：附件 -> 知识库 -> 网络/学术检索。
    formatted_reference_blocks = []
    local_markers = []
    web_markers = []
    reference_index = 0
    for i, text in enumerate(attachments or []):
        formatted_reference_blocks.append(
            f"### 参考来源 {reference_index + 1}\n"
            f"引用标记: ##{reference_index}$$\n"
            "来源类型: 用户上传附件\n"
            f"标题: 用户上传附件 {i + 1}\n"
            f"内容: {str(text or '')[:DEEP_REFERENCE_BLOCK_CHARS]}"
        )
        reference_index += 1

    for ref in all_kb_refs:
        local_markers.append(reference_index)
        formatted_reference_blocks.append(
            f"### 参考来源 {reference_index + 1}\n"
            f"引用标记: ##{reference_index}$$\n"
            "来源类型: 本地知识库\n"
            f"标题: {ref.get('document_name', 'N/A')}\n"
            f"内容: {ref.get('content_with_weight', '')[:DEEP_REFERENCE_BLOCK_CHARS]}"
        )
        reference_index += 1

    for ref in all_web_refs:
        web_markers.append(reference_index)
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
        formatted_reference_blocks.append(
            f"### 参考来源 {reference_index + 1}\n"
            f"引用标记: ##{reference_index}$$\n"
            "来源类型: 网络/学术检索\n"
            f"标题: {ref.get('title', 'N/A')}\n"
            f"{metadata_text}"
            f"摘要: {ref.get('content', '')[:DEEP_REFERENCE_BLOCK_CHARS]}"
        )
        reference_index += 1

    formatted_memory = "\n\n---\n\n".join(formatted_reference_blocks) if formatted_reference_blocks else "（无检索结果）"
    citation_quota_instruction = _build_citation_quota_instruction(
        local_markers,
        web_markers,
        all_kb_refs,
        all_web_refs,
        effective_web_search,
    )

    final_prompt = f'''
        你是一个EGC（Engineered Geopolymer Composites，
        高延性地聚合物复合材料）力学性能研究专家助手。
        负责根据用户的问题和提供的学术文献内容生成专业回答。
        {doc_instruction}
        {citation_quota_instruction}

        回答篇幅与完整性要求（深度探索模式）：
        - 除非用户明确要求简短，或检索内容严重不足，不要给出短答；请写成结构完整的研究型回答。
        - 回答通常应不少于1200个中文字，并优先使用小标题、表格和分层段落组织。
        - 至少覆盖：核心结论、证据汇总表、本地文献与网络/学术检索的交叉印证、关键力学性能范围、
          配比/纤维/养护条件影响、机理解释、工程或实验建议、局限性与后续验证需求。
        - 如果问题涉及对比或优化，请给出可操作建议，并说明每条建议对应的依据、适用边界和不确定性。
        - 不要为了拉长篇幅重复同一句话；扩展内容必须来自参考来源、文档数据或清楚标注的不确定推断。

        请严格按照以下要求生成回答：
        1. 基于提供的参考内容进行回答，如果原文没有参考内容，
           根据你自己的专业知识进行回答
        2. 所有力学性能数值必须注明数据来源（论文/实验编号），并在句末使用对应引用标记
           （例如 ##0$$、##1$$，前端会渲染为 [1]、[2]）
        3. 对比不同配比的性能时优先使用表格呈现
        4. 分析机理时引用纤维桥接、基体-纤维界面、应变硬化等概念
        5. 如数据不足以给出确切结论，明确指出不确定性范围
        6. 优化建议应说明依据和可能的改善幅度
        7. 使用专业的科学分析语言，避免夸张的销售话术
        8. 只要检索参考内容中存在"引用标记"，关键结论、数据、对比判断后必须使用这些标记引用来源；
           不要编造不存在的引用标记，不要使用普通 [1] 或 URL 作为正文引用

        检索参考内容：
        {formatted_memory}

        用户问题：{user_query}

    '''

    logger.info(
        "Prepared deep research response: actions=%s local_refs=%s web_refs=%s prompt_chars=%s",
        len(actions),
        len(all_kb_refs),
        len(all_web_refs),
        len(final_prompt),
    )

    completion = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "user", "content": final_prompt}
        ],
        stream=True,
    )

    # 保存引用数据到 DB（与 ai_search 路径格式一致）
    docs = all_kb_refs
    persisted = False

    from service.core.chat import _persist_chat_turn

    try:
        for chunk in completion:
            if chunk.choices[0].finish_reason == "stop":
                citation_appendix = _build_citation_coverage_appendix(
                    answer_content,
                    local_markers,
                    web_markers,
                    all_kb_refs,
                    all_web_refs,
                    effective_web_search,
                )
                if citation_appendix:
                    answer_content += citation_appendix
                    message = {
                        "role": "assistant",
                        "content": citation_appendix,
                        "thinking": False,
                    }
                    yield f"event: message\ndata: {json.dumps(message)}\n\n"

                if session_id and user_id and answer_content and not persisted:
                    try:
                        _persist_chat_turn(
                            session_id,
                            user_query,
                            answer_content,
                            docs,
                            [],
                            reasoning_content,
                            user_id,
                            all_web_refs,
                            attachments,
                        )
                        persisted = True
                    except Exception as e:
                        logger.exception("Failed to persist deep research conversation: %s", e)
                completed = True
                yield "event: end\ndata: [DONE]\n\n"
                break
            else:
                delta = chunk.choices[0].delta
                if delta.content:
                    answer_content += delta.content or ""
                    message = {
                        "role": "assistant",
                        "content": delta.content,
                        "thinking": False,
                    }
                    json_message = json.dumps(message)
                    yield f"event: message\ndata: {json_message}\n\n"
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content or ""
                    message = {
                        "role": "assistant",
                        "content": delta.reasoning_content,
                        "thinking": True,
                    }
                    json_message = json.dumps(message)
                    yield f"event: message\ndata: {json_message}\n\n"
    finally:
        # 流中断或异常退出时，保存已有内容防止丢失
        if not persisted and answer_content and session_id and user_id:
            try:
                _persist_chat_turn(
                    session_id,
                    user_query,
                    answer_content,
                    docs,
                    [],
                    reasoning_content,
                    user_id,
                    all_web_refs,
                    attachments,
                )
                persisted = True
            except Exception:
                logger.exception("Failed to persist interrupted deep research response")
