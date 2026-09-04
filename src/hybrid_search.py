"""Hybrid semantic and lexical retrieval using Reciprocal Rank Fusion."""

from src.lexical_search import lexical_search
from src.semantic_search import semantic_search


DEFAULT_RRF_K = 60
DEFAULT_SEMANTIC_CANDIDATES = 8
DEFAULT_LEXICAL_CANDIDATES = 8


def reciprocal_rank_fusion(semantic_results, lexical_results, rrf_k=DEFAULT_RRF_K):
    if not isinstance(rrf_k, int) or rrf_k < 1:
        raise ValueError("rrf_k must be a positive integer")

    fused = {}
    for result in semantic_results:
        item = fused.setdefault(result["id"], dict(result))
        item["rrf_score"] = item.get("rrf_score", 0.0) + 1 / (
            rrf_k + result["semantic_rank"]
        )

    for result in lexical_results:
        item = fused.setdefault(result["id"], dict(result))
        item.update(
            {
                "lexical_rank": result["lexical_rank"],
                "lexical_score": result["lexical_score"],
            }
        )
        item["rrf_score"] = item.get("rrf_score", 0.0) + 1 / (
            rrf_k + result["lexical_rank"]
        )

    for item in fused.values():
        item.setdefault("semantic_rank", None)
        item.setdefault("semantic_score", None)
        item.setdefault("similarity", item["semantic_score"])
        item.setdefault("lexical_rank", None)
        item.setdefault("lexical_score", None)

    return sorted(
        fused.values(),
        key=lambda item: (-item["rrf_score"], item["id"]),
    )


def hybrid_search(
    query,
    top_k=5,
    semantic_candidates=DEFAULT_SEMANTIC_CANDIDATES,
    lexical_candidates=DEFAULT_LEXICAL_CANDIDATES,
    rrf_k=DEFAULT_RRF_K,
):
    if not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer between 1 and 20")

    semantic_results = semantic_search(query, semantic_candidates)
    lexical_results = lexical_search(query, lexical_candidates)
    return reciprocal_rank_fusion(semantic_results, lexical_results, rrf_k)[:top_k]
