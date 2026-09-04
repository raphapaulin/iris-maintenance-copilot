"""Run live semantic-search checks against InterSystems IRIS."""

from src.semantic_search import semantic_search


VALIDATION_CASES = [
    (
        "high vibration at the motor drive-end bearing",
        {"bearing", "alignment", "motor vibration"},
    ),
    (
        "pump makes crackling noise and discharge pressure fluctuates",
        {"cavitation"},
    ),
    (
        "fan vibration after dirt accumulated on the blades",
        {"blade buildup", "imbalance", "rotor imbalance"},
    ),
]


def preview(text, length=180):
    return text if len(text) <= length else text[: length - 3] + "..."


def validate_searches():
    for query, expected_phrases in VALIDATION_CASES:
        results = semantic_search(query, top_k=3)
        if not results:
            raise AssertionError(f"No results returned for query: {query}")

        print(f"\nQuery: {query}")
        for rank, result in enumerate(results, start=1):
            print(
                f"{rank}. [{result['similarity']:.4f}] "
                f"{result['source']} / {result['title']}"
            )
            print(f"   {preview(result['content'])}")

        evidence = " ".join(
            f"{result['title']} {result['document_section']} {result['content']}".lower()
            for result in results
        )
        if not any(phrase in evidence for phrase in expected_phrases):
            raise AssertionError(
                f"Top results were not semantically reasonable for query: {query}"
            )


def main():
    try:
        validate_searches()
    except Exception as error:
        print(f"\nVector search validation FAILED: {error}")
        return 1

    print("\nVector search validation SUCCEEDED for all queries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
