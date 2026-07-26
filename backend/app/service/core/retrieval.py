
from service.core.rag.nlp.search_v2 import Dealer
from service.core.rag.utils.es_conn import ESConnection

import json
import logging
import os
import time

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default

# 创建 ElasticsearchConnection 实例
es_connection = ESConnection()

# 创建 Dealer 实例
dealer = Dealer(dataStore=es_connection)


def retrieve_content(indexNames: str, question: str, page_size: int | None = None, top_k: int | None = None):
    started = time.perf_counter()
    page_size = max(1, page_size) if page_size is not None else _env_int("RAG_PAGE_SIZE", 5)
    top_k = max(1, top_k) if top_k is not None else _env_int("RAG_TOP_K", 30)
    remote_rerank = _env_bool("RAG_ENABLE_REMOTE_RERANK", False)

    # 执行搜索
    results = dealer.retrieval(question = question,
                               embd_mdl = None,
                               tenant_ids = indexNames,
                               kb_ids = None,
                               vector_similarity_weight=0.6,
                               page = 1,
                               page_size = page_size,
                               top = top_k,
                               rerank_mdl = object() if remote_rerank else None,
    )
    logger.info(
        "RAG retrieve_content finished index=%s chunks=%s remote_rerank=%s elapsed=%.2fs",
        indexNames,
        len(results.get("chunks", [])),
        remote_rerank,
        time.perf_counter() - started,
    )

    # 提取 chunks 中的信息
    extracted_data = []


    for i, chunk in enumerate(results['chunks'], start=1):
        content_with_weight = chunk.get('content_with_weight', 'N/A')
        # similarity = chunk.get('similarity', 'N/A')
        # vector_similarity = chunk.get('vector_similarity', 'N/A')
        # term_similarity = chunk.get('term_similarity', 'N/A')
        doc_id = chunk.get('doc_id', 'N/A')
        docnm = chunk.get('docnm_kwd', 'N/A')
        if isinstance(docnm, list):
            docnm = docnm[0] if docnm else 'N/A'
        docnm = str(docnm).split("/")[-1]

        message = {
            "id": i,
            "document_id": doc_id,
            "document_name": docnm,
            'content_with_weight': content_with_weight,
        }
        
        extracted_data.append(message)

    return extracted_data


if __name__ == '__main__':
    res = retrieve_content(question="世运电路成长性如何", indexNames="test01")
    print(res)
    
    # 将提取的数据写入到文件
    # with open("output.txt", "w", encoding="utf-8") as file:
    #     for data in extracted_data:
    #         file.write(f"content_with_weight: {data['content_with_weight']}\n")
    #         file.write(f"similarity: {data['similarity']}\n")
    #         file.write(f"vector_similarity: {data['vector_similarity']}\n")
    #         file.write(f"term_similarity: {data['term_similarity']}\n")
    #         file.write("\n")
    
    # print("结果已写入到 output.txt 文件中")
