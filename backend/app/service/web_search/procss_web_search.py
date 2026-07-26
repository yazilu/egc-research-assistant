from service.web_search.web_search import serper_search, process_search_results
from service.web_search.academic_search import (
    deduplicate_snippets,
    search_academic_literature,
)
import chromadb
import logging
import uuid
from typing import List
from service.core.rag.nlp.model import generate_embedding


logger = logging.getLogger(__name__)

ACADEMIC_INTENT_HINTS = [
    "文献",
    "论文",
    "综述",
    "最新",
    "近年",
    "研究进展",
    "paper",
    "papers",
    "literature",
    "review",
    "latest",
    "recent",
    "publication",
    "publications",
]

# 自定义嵌入函数类（适配 ChromaDB）
class CustomEmbeddingFunction:
    def __init__(self):
        pass

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        for text in input:
            embedding = generate_embedding(text)
            if embedding is not None:
                # 确保返回的是列表格式
                if isinstance(embedding, list):
                    embeddings.append(embedding)
                else:
                    # 如果是其他格式（如numpy数组），转换为列表
                    embeddings.append(embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding))
            else:
                # 如果生成失败，返回一个全零向量
                embeddings.append([0.0] * 1024)  # 假设维度为 1024
        return embeddings
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        return self.__call__(texts)
    
    def embed_query(self, input: str) -> List[float]:
        """嵌入单个查询文本"""
        embedding = generate_embedding(input)
        if embedding is not None:
            # 确保返回的是列表格式
            if isinstance(embedding, list):
                return embedding
            else:
                # 如果是其他格式（如numpy数组），转换为列表
                return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        else:
            # 如果生成失败，返回一个全零向量
            return [0.0] * 1024  # 假设维度为 1024

def _safe_metadata(snippet: dict) -> dict:
    metadata = {
        "title": snippet.get("title", ""),
        "url": snippet.get("url", ""),
        "content": snippet.get("content", ""),
        "source": snippet.get("source", "web"),
        "year": snippet.get("year", ""),
        "doi": snippet.get("doi", ""),
    }
    return {key: str(value)[:5000] for key, value in metadata.items() if value is not None}


def _embedding_text(snippet: dict) -> str:
    title = snippet.get("title", "")
    source = snippet.get("source", "")
    year = snippet.get("year", "")
    doi = snippet.get("doi", "")
    content = snippet.get("content", "")
    return "\n".join(
        part
        for part in [
            f"Title: {title}" if title else "",
            f"Source: {source}" if source else "",
            f"Year: {year}" if year else "",
            f"DOI: {doi}" if doi else "",
            content,
        ]
        if part
    )


def collect_web_and_academic_snippets(question: str):
    academic_snippets = []
    web_snippets = []
    related_questions = []

    try:
        search_results = serper_search(question)
        web_snippets, related_questions = process_search_results(search_results, original_query=question)
    except Exception as exc:
        logger.warning("Serper search failed, continuing with academic results only: %s", exc)

    should_try_academic = len(web_snippets) < 5 or any(
        hint in (question or "").lower()
        for hint in ACADEMIC_INTENT_HINTS
    )
    if should_try_academic:
        try:
            academic_snippets = search_academic_literature(question)
        except Exception as exc:
            logger.warning("Academic search failed, continuing with web search only: %s", exc)

    snippets = deduplicate_snippets([*academic_snippets, *web_snippets])
    return snippets, related_questions


def store_and_query_snippets(question: str, top_k: int = 5):
    """
    将 snippets 存储到 ChromaDB，并与 question 计算相似度，返回前 top_k 条最相关的结果。
    """
    custom_embedding_fn = CustomEmbeddingFunction()
    chroma_client = chromadb.Client()

    snippets, related_questions = collect_web_and_academic_snippets(question)

    if not snippets:
        return [], related_questions

    # 使用 uuid 避免并发请求的集合名冲突
    collection_name = f"web_search_{uuid.uuid4().hex[:8]}"
    collection = chroma_client.create_collection(
        name=collection_name,
        embedding_function=custom_embedding_fn,
    )

    try:
        try:
            for idx, snippet in enumerate(snippets):
                collection.add(
                    documents=[_embedding_text(snippet)],
                    metadatas=[_safe_metadata(snippet)],
                    ids=[str(idx)],
                )

            query_embed = custom_embedding_fn.embed_query(question)
            results = collection.query(
                query_embeddings=[query_embed],
                n_results=top_k,
            )

            top_snippets = []
            for i in range(len(results["ids"][0])):
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                top_snippets.append({
                    "title": metadata["title"],
                    "url": metadata["url"],
                    "content": metadata.get("content", content),
                    "source": metadata.get("source", ""),
                    "year": metadata.get("year", ""),
                    "doi": metadata.get("doi", ""),
                })
            return top_snippets, related_questions
        except Exception as exc:
            logger.warning("Web snippets rerank failed, returning collected snippets directly: %s", exc)
            return snippets[:top_k], related_questions
    finally:
        try:
            chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass
