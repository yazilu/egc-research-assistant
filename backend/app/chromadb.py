"""Minimal in-process ChromaDB compatibility layer for local Windows startup.

The application only needs an ephemeral collection for ranking web snippets.
Installing the real chromadb package on this machine requires compiling
chroma-hnswlib, so this module implements the small API surface used by
service.web_search.procss_web_search.
"""

from __future__ import annotations

import math
from typing import Any, Iterable


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    dot = sum(left[i] * right[i] for i in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class _Collection:
    def __init__(self, embedding_function: Any | None = None) -> None:
        self._embedding_function = embedding_function
        self._items: list[dict[str, Any]] = []

    def add(
        self,
        documents: Iterable[str],
        metadatas: Iterable[dict[str, Any]],
        ids: Iterable[str],
    ) -> None:
        docs = list(documents)
        metadata_list = list(metadatas)
        id_list = list(ids)
        embeddings = (
            self._embedding_function.embed_documents(docs)
            if self._embedding_function
            else [[0.0] for _ in docs]
        )
        for doc, metadata, item_id, embedding in zip(docs, metadata_list, id_list, embeddings):
            self._items.append(
                {
                    "id": item_id,
                    "document": doc,
                    "metadata": metadata,
                    "embedding": list(embedding),
                }
            )

    def query(self, query_embeddings: list[list[float]], n_results: int) -> dict[str, Any]:
        batches = []
        for query_embedding in query_embeddings:
            ranked = sorted(
                self._items,
                key=lambda item: _cosine_similarity(query_embedding, item["embedding"]),
                reverse=True,
            )[:n_results]
            batches.append(ranked)
        return {
            "ids": [[item["id"] for item in batch] for batch in batches],
            "documents": [[item["document"] for item in batch] for batch in batches],
            "metadatas": [[item["metadata"] for item in batch] for batch in batches],
        }


class Client:
    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def create_collection(
        self,
        name: str,
        embedding_function: Any | None = None,
    ) -> _Collection:
        collection = _Collection(embedding_function)
        self._collections[name] = collection
        return collection

    def delete_collection(self, name: str) -> None:
        self._collections.pop(name, None)
