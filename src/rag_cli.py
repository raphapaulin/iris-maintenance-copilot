"""Command-line demonstration of grounded maintenance assessment."""

import argparse

from src.rag_service import generate_assessment


DEFAULT_QUERY = "High vibration at the drive-end bearing of the main conveyor motor"


def print_assessment(result):
    assessment = result["assessment"]
    print("\nMaintenance Assessment")
    print("----------------------")
    print(f"\nObserved issue:\n{assessment['observed_issue']}")
    print(f"\nAssessment:\n{assessment['assessment']}")

    print("\nPossible causes:")
    for item in assessment["likely_causes"]:
        print(f"- {item['cause']} [{', '.join(item['evidence_ids'])}]")

    print("\nRecommended checks:")
    for position, item in enumerate(assessment["recommended_checks"], start=1):
        print(f"{position}. {item['check']} [{', '.join(item['evidence_ids'])}]")

    print(f"\nEvidence coverage:\n{assessment['evidence_coverage']}")
    if result["weak_evidence"]:
        print(f"\nRetrieval note:\n{result['context_note']}")
    print("\nEvidence used:")
    for item in result["evidence"]:
        print(f"{item['evidence_id']} — {item['title']} (chunk {item['chunk_id']})")

    print("\nLimitations:")
    for limitation in assessment["limitations"]:
        print(f"- {limitation}")
    print(f"\nSafety note:\n{assessment['safety_note']}")


def main():
    parser = argparse.ArgumentParser(description="Grounded maintenance assessment")
    parser.add_argument("query", nargs="?", default=DEFAULT_QUERY)
    args = parser.parse_args()

    try:
        result = generate_assessment(args.query)
    except Exception as error:
        print(f"Grounded generation FAILED: {error}")
        return 1

    print_assessment(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
