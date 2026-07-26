from dotenv import load_dotenv
import html
import os
import http.client
import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â",
    "ä¸",
    "æ",
    "ç",
    "è",
    "é",
    "ï¼",
    "\ufffd",
)

MOJIBAKE_REPLACEMENTS = {
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u0080\u009c": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00e2\u0080\u009d": '"',
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u0080\u0098": "'",
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u0080\u0099": "'",
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u0080\u0093": "-",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u0080\u0094": "-",
    "\u00e2\u20ac\u00a6": "...",
    "\u00e2\u0080\u00a6": "...",
    "\u00c2\u00b7": "·",
    "\u00c2 ": " ",
    "\u00c2": "",
    "\ufffd": "",
}


def _mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)


def _repair_latin1_mojibake(text: str) -> str:
    if not text or not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text
    best = text
    best_score = _mojibake_score(text)
    for encoding in ("cp1252", "latin1"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
        repaired_score = _mojibake_score(repaired)
        if repaired_score < best_score:
            best = repaired
            best_score = repaired_score
    return best


def _clean_search_text(value) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = _repair_latin1_mojibake(text)
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


EGC_PATTERN = re.compile(r"(?i)(?<![A-Za-z0-9_])egc(?![A-Za-z0-9_])")
EGC_MATERIAL_HINTS = [
    "engineered geopolymer",
    "geopolymer",
    "geopolymer composite",
    "high ductility geopolymer",
    "mechanical properties",
    "strain hardening",
    "fiber bridging",
    "fly ash",
    "slag",
    "metakaolin",
    "地聚合物",
    "高延性",
    "粉煤灰",
    "矿渣",
    "偏高岭土",
    "力学性能",
    "应变硬化",
    "纤维桥接",
]
EGC_MEDICAL_HINTS = [
    "early gastric cancer",
    "gastric cancer",
    "stomach cancer",
    "endoscopic",
    "gastrectomy",
    "oncology",
    "carcinoma",
    "胃癌",
    "早期胃癌",
    "内镜",
    "胃切除",
    "肿瘤",
    "癌",
]
RECENT_LITERATURE_HINTS = [
    "最新",
    "近年",
    "近期",
    "进展",
    "文献",
    "论文",
    "综述",
    "研究",
    "latest",
    "recent",
    "new",
    "paper",
    "papers",
    "literature",
    "publication",
    "publications",
    "review",
]
RELATED_CEMENTITIOUS_HINTS = [
    "similar",
    "related",
    "comparison",
    "compare",
    "versus",
    "vs",
    "cementitious",
    "concrete",
    "UHPC",
    "ECC",
    "SHCC",
    "UHPFRC",
    "HPFRCC",
    "相似",
    "类似",
    "相关",
    "对比",
    "比较",
    "水泥基",
    "混凝土",
    "超高性能混凝土",
    "工程水泥基复合材料",
]


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _is_egc_material_query(query: str) -> bool:
    text = query.lower()
    has_egc = bool(EGC_PATTERN.search(query))
    has_material_hint = _contains_any(text, EGC_MATERIAL_HINTS)
    has_medical_hint = _contains_any(text, EGC_MEDICAL_HINTS)
    return (has_egc or has_material_hint) and not has_medical_hint


def normalize_egc_search_query(query: str) -> str:
    """
    Disambiguate EGC for this app's materials domain before sending it to Serper.

    Bare "EGC" is dominated by medical search results for early gastric cancer.
    Adding the full materials terminology and negative medical terms keeps web
    search aligned with Engineered Geopolymer Composites.
    """
    query = " ".join(str(query or "").split())
    if not query or not _is_egc_material_query(query):
        return query

    lower_query = query.lower()
    additions = []

    if "engineered geopolymer" not in lower_query:
        additions.append('"Engineered Geopolymer Composites"')
        additions.append('"high ductility geopolymer composites"')
    if "mechanical properties" not in lower_query and "力学性能" not in lower_query:
        additions.append('"mechanical properties"')
    if "strain hardening" not in lower_query and "应变硬化" not in lower_query:
        additions.append('"strain hardening"')

    if _contains_any(lower_query, [term.lower() for term in RELATED_CEMENTITIOUS_HINTS]):
        additions.append('"engineered cementitious composites"')
        additions.append('"ultra-high performance concrete"')
        additions.append('"strain-hardening cementitious composites"')
        additions.append('"ultra-high performance fiber-reinforced concrete"')

    if _contains_any(lower_query, RECENT_LITERATURE_HINTS):
        current_year = datetime.now().year
        additions.append(f"{current_year} {current_year - 1}")
        additions.append("research paper review")

    exclusions = [
        '-"early gastric cancer"',
        '-"gastric cancer"',
        "-endoscopic",
        "-gastrectomy",
        "-胃癌",
        "-内镜",
    ]
    expanded = " ".join([query, *additions, *exclusions])
    return expanded


def _simple_egc_search_query(query: str) -> str:
    query = " ".join(str(query or "").split())
    lower_query = query.lower()
    terms = []

    if _is_egc_material_query(query):
        terms.append("Engineered Geopolymer Composites")
    if "ecc" in lower_query:
        terms.append("Engineered Cementitious Composites")
    if "uhpc" in lower_query:
        terms.append("Ultra-high performance concrete")
    if "shcc" in lower_query:
        terms.append("Strain-hardening cementitious composites")
    if "uhpfrc" in lower_query:
        terms.append("Ultra-high performance fiber-reinforced concrete")
    if "不同" in query or "区别" in query or "对比" in query or "compare" in lower_query:
        terms.append("comparison")

    if not terms:
        return query
    return " ".join([query, *terms])


def _is_medical_egc_result(result_text: str) -> bool:
    text = result_text.lower()
    return _contains_any(text, EGC_MEDICAL_HINTS) and not _contains_any(text, EGC_MATERIAL_HINTS)


def serper_search(q="apple inc", hl="zh-cn",num = 20):
    """
    使用 Serper API 进行常规搜索的函数

    参数:
        q (str): 搜索关键词，默认为 "apple inc"
        hl (str): 语言，默认为 "zh-cn"（中文）

    返回:
        dict: 搜索结果的 JSON 数据
    """
    return make_request(q, hl, "/search", num)

def serper_images(q="apple inc", hl="zh-cn"):
    """
    使用 Serper API 进行图片搜索的异步函数

    参数:
        q (str): 搜索关键词，默认为 "apple inc"
        hl (str): 语言，默认为 "zh-cn"（中文）

    返回:
        dict: 图片搜索结果的 JSON 数据
    """
    return make_request(q, hl, "/images")

def serper_videos(q="apple inc", hl="zh-cn"):
    """
    使用 Serper API 进行视频搜索的异步函数

    参数:
        q (str): 搜索关键词，默认为 "apple inc"
        hl (str): 语言，默认为 "zh-cn"（中文）

    返回:
        dict: 视频搜索结果的 JSON 数据
    """
    return make_request(q, hl, "/videos")

def make_request(q, hl, endpoint, num=10):
    """
    发送请求到 Serper API 的通用函数

    参数:
        q (str): 搜索关键词
        hl (str): 语言
        endpoint (str): API 的 endpoint

    返回:
        dict: 搜索结果的 JSON 数据
    """
    # 加载.env文件
    load_dotenv()

    api_key = os.getenv("SERPER_API_KEY")

    normalized_q = normalize_egc_search_query(q)
    query_candidates = [normalized_q]
    simple_q = _simple_egc_search_query(q)
    if simple_q != normalized_q:
        query_candidates.append(simple_q)

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    last_status = None
    last_body = ""
    for index, candidate_q in enumerate(query_candidates):
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": candidate_q,
            "hl": hl,
            "num": num
        }, ensure_ascii=False).encode("utf-8")
        conn.request("POST", endpoint, payload, headers)
        res = conn.getresponse()
        data = res.read()
        body = data.decode("utf-8")
        conn.close()

        if res.status == 200:
            parsed = json.loads(body)
            if (
                endpoint == "/search"
                and index == 0
                and len(query_candidates) > 1
                and not parsed.get("organic")
            ):
                logger.warning("Serper advanced query returned no organic results; retrying with simplified query")
                continue
            if candidate_q != q:
                logger.info("Serper query normalized: original=%s normalized=%s", q[:80], candidate_q[:160])
            logger.info(f"Serper API success: endpoint={endpoint}, q={candidate_q[:80]}")
            return parsed

        last_status = res.status
        last_body = body
        if index == 0 and "Query pattern not allowed" in body:
            logger.warning("Serper rejected advanced query; retrying with simplified query")
            continue
        logger.error(f"Serper API error: status={res.status}, body={body[:500]}")
        raise RuntimeError(f"搜索引擎请求失败 (HTTP {res.status})，请检查 API Key 是否有效或是否超过配额")
    else:
        logger.error(f"Serper API error: status={last_status}, body={last_body[:500]}")
        raise RuntimeError(f"搜索引擎请求失败 (HTTP {last_status})，请检查 API Key 是否有效或是否超过配额")


def process_search_results(search_results, original_query=None):
    """
    处理 search 查询的返回值，返回两个列表，第一个是 snippet，第二个是 question。

    参数:
        search_results (dict): search 查询的返回值，是一个 JSON 格式的字典。

    返回:
        tuple: 一个包含两个列表的元组，第一个列表是 snippet，第二个列表是 question。
    """
    snippets = []
    questions = []

    material_query = _is_egc_material_query(original_query or "")

    # 处理 organic 搜索结果，提取 snippet
    if 'organic' in search_results:
        for result in search_results['organic']:
            snippet = _clean_search_text(result.get('snippet', '') or result.get('description', ''))
            if not snippet:
                continue
            title = _clean_search_text(result.get('title', ''))
            url = _clean_search_text(result.get('link', ''))
            result_text = " ".join([title, url, snippet])
            if material_query and _is_medical_egc_result(result_text):
                logger.debug("Filtered medical EGC search result: %s", title)
                continue
            message = {
                "title": title,
                "url": url,
                "content": snippet,
            }
            snippets.append(message)


    # 处理相关问题，提取 question
    if 'peopleAlsoAsk' in search_results:
        for question_data in search_results['peopleAlsoAsk']:
            if 'question' in question_data:
                question = _clean_search_text(question_data['question'])
                if material_query and _is_medical_egc_result(question):
                    continue
                questions.append(question)

    return snippets, questions

if __name__=='__main__':
    # 假设 search_results 是 search 函数的返回值
    search_results = serper_search(q="人工智能", hl="zh-cn")
    snippets, questions = process_search_results(search_results)
    
    # 打印 snippet 列表
    print("Snippets:")
    for snippet in snippets:
        print(snippet)
    
    # 打印 question 列表
    print("\nQuestions:")
    for question in questions:
        print(question)
