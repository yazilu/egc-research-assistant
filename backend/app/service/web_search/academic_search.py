import logging
import os
import re
import time
from typing import Any

import requests
from dotenv import load_dotenv

from service.web_search.web_search import (
    EGC_MATERIAL_HINTS,
    EGC_MEDICAL_HINTS,
    RECENT_LITERATURE_HINTS,
    _clean_search_text,
    _contains_any,
    _is_egc_material_query,
)


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 4
REQUEST_RETRIES = 1
MAX_QUERY_CHARS = 360

GENERIC_ACADEMIC_WORDS = {
    "latest",
    "recent",
    "new",
    "paper",
    "papers",
    "literature",
    "publication",
    "publications",
    "review",
    "research",
    "study",
    "studies",
    "article",
    "articles",
    "progress",
    "advance",
    "advances",
    "egc",
}

EGC_BASE_TERMS = [
    "Engineered Geopolymer Composites",
    "high ductility geopolymer composites",
    "geopolymer composites",
    "mechanical properties",
    "strain hardening",
]

RELATED_CEMENTITIOUS_BASE_TERMS = [
    "cementitious composites",
    "engineered cementitious composites",
    "ultra-high performance concrete",
    "strain-hardening cementitious composites",
    "ultra-high performance fiber-reinforced concrete",
]

CEMENTITIOUS_ACRONYM_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(UHPC|ECC|SHCC|UHPFRC|HPFRCC|FRCC)(?![A-Za-z0-9_])"
)

CEMENTITIOUS_STRONG_HINTS = [
    *EGC_MATERIAL_HINTS,
    "engineered cementitious composite",
    "engineered cementitious composites",
    "strain-hardening cementitious composite",
    "strain hardening cementitious composite",
    "ultra-high performance concrete",
    "ultra high performance concrete",
    "ultrahigh-performance concrete",
    "ultra-high performance fiber-reinforced concrete",
    "ultra high performance fiber reinforced concrete",
    "high performance fiber reinforced cementitious composite",
    "fiber reinforced cementitious composite",
    "fiber-reinforced cementitious composite",
    "cementitious composite",
    "cement-based composite",
    "cement based composite",
    "alkali-activated material",
    "alkali activated material",
    "geopolymer concrete",
    "水泥基复合材料",
    "纤维增强水泥基",
    "工程水泥基复合材料",
    "应变硬化水泥基",
    "超高性能混凝土",
    "超高性能纤维增强混凝土",
]

CEMENTITIOUS_WEAK_HINTS = [
    "cementitious",
    "cement-based",
    "cement based",
    "concrete",
    "mortar",
    "cement paste",
    "水泥基",
    "混凝土",
    "砂浆",
    "水泥浆",
]

RELATED_CONTEXT_HINTS = [
    "similar",
    "related",
    "comparison",
    "compare",
    "versus",
    "vs",
    "review",
    "progress",
    "latest",
    "recent",
    "cementitious",
    "concrete",
    "相似",
    "类似",
    "相关",
    "对比",
    "比较",
    "综述",
    "进展",
    "最新",
    "水泥基",
    "混凝土",
]

WEAK_MATERIAL_CONTEXT_HINTS = [
    "similar",
    "related",
    "comparison",
    "compare",
    "versus",
    "vs",
    "cementitious",
    "concrete",
    "mortar",
    "相似",
    "类似",
    "相关",
    "对比",
    "比较",
    "水泥基",
    "混凝土",
    "砂浆",
]

CHINESE_TERM_TRANSLATIONS = {
    "\u5730\u805a\u5408\u7269": "geopolymer",
    "\u6c34\u6ce5\u57fa": "cementitious",
    "\u6c34\u6ce5\u57fa\u590d\u5408\u6750\u6599": "cementitious composites",
    "\u6df7\u51dd\u571f": "concrete",
    "\u8d85\u9ad8\u6027\u80fd\u6df7\u51dd\u571f": "ultra-high performance concrete",
    "\u8d85\u9ad8\u6027\u80fd\u7ea4\u7ef4\u589e\u5f3a\u6df7\u51dd\u571f": "ultra-high performance fiber-reinforced concrete",
    "\u5de5\u7a0b\u6c34\u6ce5\u57fa\u590d\u5408\u6750\u6599": "engineered cementitious composites",
    "\u5e94\u53d8\u786c\u5316\u6c34\u6ce5\u57fa": "strain-hardening cementitious composites",
    "\u9ad8\u5ef6\u6027": "high ductility",
    "\u7c89\u7164\u7070": "fly ash",
    "\u77ff\u6e23": "slag",
    "\u504f\u9ad8\u5cad\u571f": "metakaolin",
    "\u529b\u5b66\u6027\u80fd": "mechanical properties",
    "\u6297\u538b\u5f3a\u5ea6": "compressive strength",
    "\u6297\u62c9\u5f3a\u5ea6": "tensile strength",
    "\u62c9\u4f38\u5e94\u53d8": "tensile strain",
    "\u6781\u9650\u62c9\u4f38\u5e94\u53d8": "ultimate tensile strain",
    "\u5f2f\u66f2": "flexural",
    "\u97e7\u6027": "ductility",
    "\u7ea4\u7ef4": "fiber",
    "\u805a\u4e59\u70ef\u9187": "PVA",
    "\u6386\u91cf": "content",
    "\u6c34\u80f6\u6bd4": "water binder ratio",
    "\u7802\u80f6\u6bd4": "sand binder ratio",
    "\u517b\u62a4": "curing",
    "\u5e94\u53d8\u786c\u5316": "strain hardening",
    "\u6865\u63a5": "bridging",
    "\u77f3\u82f1\u7802": "quartz sand",
    "\u7eb3\u7c73": "nano",
}

MEDICAL_BLOCKLIST = [
    "early gastric cancer",
    "gastric cancer",
    "stomach cancer",
    "endoscopic",
    "gastrectomy",
    "oncology",
    "carcinoma",
]


def _clean_text(value: Any) -> str:
    return _clean_search_text(value)


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        clean = _clean_text(value)
        key = clean.lower()
        if not clean or key in seen:
            continue
        seen.add(key)
        output.append(clean)
    return output


def _english_query_tokens(query: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+./-]*", query)
    return [
        token
        for token in tokens
        if token.lower().strip(".-/") not in GENERIC_ACADEMIC_WORDS
    ]


def normalize_academic_query(query: str) -> str:
    """Build an English-heavy query that works better in literature APIs."""
    query = " ".join(str(query or "").split())
    if not query:
        return ""

    material_query = _is_egc_material_query(query)
    parts = []

    if material_query:
        parts.extend(EGC_BASE_TERMS)
        if _needs_related_cementitious_context(query):
            parts.extend(RELATED_CEMENTITIOUS_BASE_TERMS)

    parts.extend(_english_query_tokens(query))

    for chinese_term, english_term in CHINESE_TERM_TRANSLATIONS.items():
        if chinese_term in query:
            parts.append(english_term)

    if not parts:
        parts.append(query)

    return " ".join(_dedupe_keep_order(parts))[:MAX_QUERY_CHARS]


def _academic_query_variants(query: str) -> list[str]:
    primary_query = normalize_academic_query(query)
    variants = []

    lower_query = (query or "").lower()
    has_egc = "egc" in lower_query
    acronyms = [match.group(1).upper() for match in CEMENTITIOUS_ACRONYM_PATTERN.finditer(query or "")]

    if has_egc and "ECC" in acronyms:
        variants.extend(
            [
                "engineered geopolymer composites engineered cementitious composites",
                "EGC ECC engineered geopolymer composites",
                "engineered geopolymer composites ECC comparison",
            ]
        )
    elif has_egc:
        variants.extend(
            [
                "engineered geopolymer composites",
                "high ductility geopolymer composites",
            ]
        )

    if acronyms:
        variants.append(" ".join(_dedupe_keep_order(acronyms + ["cementitious composites"])))

    variants.append(primary_query)
    return [variant for variant in _dedupe_keep_order(variants) if variant]


def _is_recent_literature_query(query: str) -> bool:
    lower_query = (query or "").lower()
    return _contains_any(lower_query, RECENT_LITERATURE_HINTS)


def _needs_related_cementitious_context(query: str) -> bool:
    lower_query = (query or "").lower()
    return _contains_any(lower_query, RELATED_CONTEXT_HINTS) or bool(
        CEMENTITIOUS_ACRONYM_PATTERN.search(query or "")
    )


def _headers(source: str) -> dict[str, str]:
    load_dotenv()
    mailto = os.getenv("CROSSREF_MAILTO", "").strip()
    user_agent = "EGC-Research-Assistant/1.0"
    if mailto:
        user_agent = f"{user_agent} (mailto:{mailto})"

    headers = {"User-Agent": user_agent}
    if source == "semantic_scholar":
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
        if api_key:
            headers["x-api-key"] = api_key
    return headers


def _get_json(source: str, url: str, params: dict[str, Any]) -> dict[str, Any]:
    last_error = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=_headers(source),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code in {403, 429}:
                logger.warning("%s academic search throttled: HTTP %s", source, response.status_code)
                return {}
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < REQUEST_RETRIES:
                time.sleep(0.5 * attempt)

    logger.warning("%s academic search failed: %s", source, last_error)
    return {}


def _openalex_abstract(inverted_index: Any) -> str:
    if not isinstance(inverted_index, dict):
        return ""
    positioned_words = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        positioned_words.extend((position, word) for position in positions)
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def _format_authors(authors: list[str], max_authors: int = 5) -> str:
    clean_authors = [author for author in authors if author]
    if not clean_authors:
        return ""
    shown = clean_authors[:max_authors]
    suffix = " et al." if len(clean_authors) > max_authors else ""
    return ", ".join(shown) + suffix


def _doi_url(doi: str) -> str:
    doi = (doi or "").strip()
    if not doi:
        return ""
    if doi.startswith("http://") or doi.startswith("https://"):
        return doi
    return f"https://doi.org/{doi}"


def _build_content(
    *,
    source: str,
    authors: str = "",
    year: str = "",
    venue: str = "",
    doi: str = "",
    abstract: str = "",
    extra: str = "",
) -> str:
    metadata = []
    if source:
        metadata.append(f"Source: {source}")
    if authors:
        metadata.append(f"Authors: {authors}")
    if year:
        metadata.append(f"Year: {year}")
    if venue:
        metadata.append(f"Venue: {venue}")
    if doi:
        metadata.append(f"DOI: {doi}")
    if extra:
        metadata.append(extra)

    content = "; ".join(metadata)
    abstract = _clean_text(abstract)
    if abstract:
        content = f"{content}. Abstract: {abstract}" if content else abstract
    return content


def _is_material_result(result: dict[str, Any], original_query: str) -> bool:
    if not _is_egc_material_query(original_query):
        return True

    combined = " ".join(
        str(result.get(key, ""))
        for key in ("title", "content", "url", "venue", "doi")
    ).lower()

    has_strong_material_signal = _contains_any(
        combined,
        CEMENTITIOUS_STRONG_HINTS,
    ) or bool(CEMENTITIOUS_ACRONYM_PATTERN.search(combined))
    has_weak_material_signal = _contains_any(combined, CEMENTITIOUS_WEAK_HINTS)
    allow_weak_material_signal = _contains_any(
        (original_query or "").lower(),
        WEAK_MATERIAL_CONTEXT_HINTS,
    ) or bool(CEMENTITIOUS_ACRONYM_PATTERN.search(original_query or ""))
    has_material_signal = has_strong_material_signal or (
        allow_weak_material_signal and has_weak_material_signal
    )
    if not has_material_signal:
        return False

    if _contains_any(combined, MEDICAL_BLOCKLIST) or _contains_any(combined, EGC_MEDICAL_HINTS):
        return has_strong_material_signal
    return True


def _normalize_result(result: dict[str, Any], original_query: str) -> dict[str, Any] | None:
    title = _clean_text(result.get("title"))
    content = _clean_text(result.get("content"))
    if not title or not content:
        return None

    normalized = {
        "title": title,
        "url": _clean_text(result.get("url")),
        "content": content,
        "source": _clean_text(result.get("source")),
        "year": _clean_text(result.get("year")),
        "doi": _clean_text(result.get("doi")),
        "venue": _clean_text(result.get("venue")),
        "academic": True,
    }
    if not _is_material_result(normalized, original_query):
        logger.debug("Filtered non-material EGC academic result: %s", title)
        return None
    return normalized


def _search_openalex(query: str, original_query: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "search": query,
        "per-page": min(limit, 25),
        "sort": "relevance_score:desc",
    }

    data = _get_json("openalex", "https://api.openalex.org/works", params)
    results = []
    for item in data.get("results", []) or []:
        authors = _format_authors(
            [
                ((author.get("author") or {}).get("display_name") or "")
                for author in item.get("authorships", []) or []
            ]
        )
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        host_venue = item.get("host_venue") or {}
        venue = source.get("display_name") or host_venue.get("display_name") or ""
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        url = (
            (item.get("open_access") or {}).get("oa_url")
            or primary_location.get("landing_page_url")
            or item.get("doi")
            or (item.get("ids") or {}).get("openalex")
            or ""
        )
        abstract = _openalex_abstract(item.get("abstract_inverted_index"))
        content = _build_content(
            source="OpenAlex",
            authors=authors,
            year=str(item.get("publication_year") or ""),
            venue=venue,
            doi=doi,
            abstract=abstract,
            extra=f"Citations: {item.get('cited_by_count')}" if item.get("cited_by_count") is not None else "",
        )
        result = _normalize_result(
            {
                "title": item.get("display_name"),
                "url": url,
                "content": content,
                "source": "OpenAlex",
                "year": item.get("publication_year"),
                "doi": doi,
                "venue": venue,
            },
            original_query,
        )
        if result:
            results.append(result)
    return results


def _crossref_year(item: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "issued"):
        parts = ((item.get(key) or {}).get("date-parts") or [])
        if parts and parts[0]:
            return str(parts[0][0])
    return ""


def _search_crossref(query: str, original_query: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "query.bibliographic": query,
        "rows": min(limit, 20),
        "select": "title,DOI,URL,author,container-title,abstract,published-print,published-online,published,issued,type,score",
    }

    data = _get_json("crossref", "https://api.crossref.org/works", params)
    items = ((data.get("message") or {}).get("items") or [])
    results = []
    for item in items:
        title_values = item.get("title") or []
        venue_values = item.get("container-title") or []
        doi = item.get("DOI") or ""
        authors = _format_authors(
            [
                " ".join(filter(None, [author.get("given", ""), author.get("family", "")]))
                for author in item.get("author", []) or []
            ]
        )
        content = _build_content(
            source="Crossref",
            authors=authors,
            year=_crossref_year(item),
            venue=venue_values[0] if venue_values else "",
            doi=doi,
            abstract=item.get("abstract") or "",
            extra=f"Type: {item.get('type')}" if item.get("type") else "",
        )
        result = _normalize_result(
            {
                "title": title_values[0] if title_values else "",
                "url": item.get("URL") or _doi_url(doi),
                "content": content,
                "source": "Crossref",
                "year": _crossref_year(item),
                "doi": doi,
                "venue": venue_values[0] if venue_values else "",
            },
            original_query,
        )
        if result:
            results.append(result)
    return results


def _search_semantic_scholar(query: str, original_query: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "query": query,
        "limit": min(limit, 20),
        "fields": ",".join(
            [
                "title",
                "year",
                "authors",
                "venue",
                "journal",
                "externalIds",
                "url",
                "abstract",
                "citationCount",
                "publicationDate",
                "openAccessPdf",
            ]
        ),
    }
    data = _get_json(
        "semantic_scholar",
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params,
    )
    results = []
    for item in data.get("data", []) or []:
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI") or ""
        open_access_pdf = item.get("openAccessPdf") or {}
        journal = item.get("journal") or {}
        venue = journal.get("name") or item.get("venue") or ""
        authors = _format_authors(
            [author.get("name", "") for author in item.get("authors", []) or []]
        )
        content = _build_content(
            source="Semantic Scholar",
            authors=authors,
            year=str(item.get("year") or ""),
            venue=venue,
            doi=doi,
            abstract=item.get("abstract") or "",
            extra=f"Citations: {item.get('citationCount')}" if item.get("citationCount") is not None else "",
        )
        result = _normalize_result(
            {
                "title": item.get("title"),
                "url": open_access_pdf.get("url") or item.get("url") or _doi_url(doi),
                "content": content,
                "source": "Semantic Scholar",
                "year": item.get("year"),
                "doi": doi,
                "venue": venue,
            },
            original_query,
        )
        if result:
            results.append(result)
    return results


def _result_fingerprint(result: dict[str, Any]) -> str:
    doi = (result.get("doi") or "").lower().replace("https://doi.org/", "").strip()
    if doi:
        return f"doi:{doi}"
    title = re.sub(r"[^a-z0-9]+", " ", (result.get("title") or "").lower()).strip()
    return f"title:{title}"


def deduplicate_snippets(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    order = []

    for snippet in snippets:
        key = _result_fingerprint(snippet)
        if not key or key == "title:":
            key = f"url:{(snippet.get('url') or '').lower()}"
        if key not in deduped:
            deduped[key] = snippet
            order.append(key)
            continue

        existing = deduped[key]
        if len(snippet.get("content", "")) > len(existing.get("content", "")):
            deduped[key] = {**existing, **snippet}

    return [deduped[key] for key in order]


def search_academic_literature(query: str, limit: int = 18) -> list[dict[str, Any]]:
    """Search public scholarly APIs and return frontend-compatible snippets."""
    query_variants = _academic_query_variants(query)
    if not query_variants:
        return []

    per_source = max(4, min(10, limit // 2))
    results = []
    for academic_query in query_variants[:2]:
        logger.info("Academic search query normalized: original=%s normalized=%s", query[:80], academic_query)
        results.extend(_search_openalex(academic_query, query, per_source))
        results.extend(_search_crossref(academic_query, query, per_source))
        results.extend(_search_semantic_scholar(academic_query, query, per_source))

        results = deduplicate_snippets(results)
        if len(results) >= limit:
            break

    return results[:limit]
