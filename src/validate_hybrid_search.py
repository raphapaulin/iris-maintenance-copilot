"""Compare semantic, lexical, and hybrid retrieval against live IRIS data."""

from src.hybrid_search import reciprocal_rank_fusion
from src.lexical_search import lexical_search
from src.semantic_search import semantic_search


VALIDATION_CASES = [
    ("high vibration at the motor drive-end bearing", {"motor", "bearing", "alignment"}),
    ("pump makes crackling noise and discharge pressure fluctuates", {"cavitation"}),
    ("fan vibration after dirt accumulated on the blades", {"imbalance", "buildup"}),
    ("cavitation centrifugal pump", {"cavitation"}),
    ("coupling misalignment", {"coupling", "misalignment", "alignment"}),
]

SEMANTIC_CANDIDATES = 5
LEXICAL_CANDIDATES = 5
FINAL_TOP_K = 5
RRF_K = 60


def print_ranked(label, results, score_key):
    print(f"\n{label}:")
    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result['source']} / {result['title']} "
            f"[{score_key}={result[score_key]:.4f}]"
        )


def print_hybrid(results):
    print("\nHybrid / RRF:")
    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result['source']} / {result['title']}")
        print(
            f"   semantic_rank={result['semantic_rank']} "
            f"semantic_score={result['semantic_score']} "
            f"lexical_rank={result['lexical_rank']} "
            f"lexical_score={result['lexical_score']} "
            f"rrf_score={result['rrf_score']:.6f}"
        )


def validate_hybrid_searches():
    for query, expected_terms in VALIDATION_CASES:
        semantic = semantic_search(query, SEMANTIC_CANDIDATES)
        lexical = lexical_search(query, LEXICAL_CANDIDATES)
        if not lexical:
            raise AssertionError(f"Lexical search returned no candidates for: {query}")

        hybrid = reciprocal_rank_fusion(semantic, lexical, RRF_K)[:FINAL_TOP_K]
        if not hybrid:
            raise AssertionError(f"Hybrid search returned no candidates for: {query}")

        print("\n" + "=" * 72)
        print(f"Query: {query}")
        print_ranked("Semantic", semantic, "semantic_score")
        print_ranked("Lexical", lexical, "lexical_score")
        print_hybrid(hybrid)

        top_evidence = " ".join(
            f"{item['title']} {item['document_section']} "
            f"{item['equipment_type']} {item['content']}".lower()
            for item in hybrid[:3]
        )
        if not any(term in top_evidence for term in expected_terms):
            raise AssertionError(f"Hybrid top evidence is irrelevant for: {query}")


def main():
    try:
        validate_hybrid_searches()
    except Exception as error:
        print(f"\nHybrid search validation FAILED: {error}")
        return 1

    print("\nHybrid search validation SUCCEEDED for all queries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
