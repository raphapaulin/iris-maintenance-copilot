"""Validate grounded-RAG components or run live retrieval plus generation."""

import argparse
import json

from src.evidence_context import format_evidence_context, select_evidence
from src.rag_service import GroundingValidationError, generate_assessment, parse_and_validate_output


VALIDATION_QUERIES = [
    "High vibration at the drive-end bearing of the main conveyor motor",
    "The cooling water pump sounds like crackling gravel and its discharge pressure is unstable",
    "The exhaust fan started vibrating after dirt accumulated on the blades",
    "The motor display shows error code ZX-991",
]


def _fixture_hybrid_result():
    return {
        "id": 1,
        "source": "controlled-test-fixture",
        "title": "Motor bearing guidance",
        "document_section": "Bearings",
        "equipment_type": "Electric motor",
        "content": "General evidence about inspecting motor bearing vibration.",
        "rrf_score": 0.03,
        "semantic_rank": 1,
        "semantic_score": 0.8,
        "lexical_rank": 1,
        "lexical_score": 2.0,
    }


def validate_components():
    for unsupported_identifier in ("QA-2048", "MTR-77"):
        selected = select_evidence(
            f"The equipment display shows error code {unsupported_identifier}",
            [_fixture_hybrid_result()],
        )
        assert selected["items"][0]["evidence_id"] == "E1"
        assert selected["weak_evidence"] is True
        assert unsupported_identifier in selected["context_note"]
        assert "Do not infer their meaning" in selected["context_note"]
        assert "[E1]" in format_evidence_context(selected)

    unsupported_identifier = "QA-2048"
    selected = select_evidence(
        f"The equipment display shows error code {unsupported_identifier}",
        [_fixture_hybrid_result()],
    )

    valid_output = json.dumps(
        {
            "observed_issue": "A reported motor display code.",
            "assessment": f"The supplied evidence does not define {unsupported_identifier}.",
            "likely_causes": [],
            "recommended_checks": [
                {
                    "check": "Use the applicable equipment documentation to identify the code.",
                    "evidence_ids": ["E1"],
                }
            ],
            "evidence_coverage": "low",
            "limitations": [
                f"{unsupported_identifier} is not present in the supplied evidence."
            ],
            "safety_note": "Follow site safety procedures before inspection.",
        }
    )
    parse_and_validate_output(valid_output, selected["items"])

    invalid_outputs = [
        "not json",
        json.dumps({"observed_issue": "missing fields"}),
        valid_output.replace('"low"', '"unsupported"'),
        valid_output.replace('"E1"', '"E99"'),
        valid_output.replace('"evidence_ids": ["E1"]', '"evidence_ids": []'),
    ]
    for output in invalid_outputs:
        try:
            parse_and_validate_output(output, selected["items"])
        except GroundingValidationError:
            continue
        raise AssertionError("An invalid controlled output was accepted")

    print("Controlled context and output-schema validation SUCCEEDED.")


def validate_live_generation():
    for query in VALIDATION_QUERIES:
        print("\n" + "=" * 72)
        print(f"Query: {query}")
        result = generate_assessment(query)
        assessment = result["assessment"]
        print(json.dumps(assessment, indent=2, ensure_ascii=False))
        print("Evidence: " + ", ".join(item["evidence_id"] for item in result["evidence"]))
        print(f"Weak evidence flag: {result['weak_evidence']}")

        if "ZX-991" in query:
            combined = " ".join(
                [assessment["assessment"], *assessment["limitations"]]
            ).lower()
            if assessment["evidence_coverage"] != "low" or not any(
                term in combined for term in ("insufficient", "not", "unknown")
            ):
                raise AssertionError("ZX-991 response did not acknowledge weak evidence")

    print("\nLive grounded-RAG validation SUCCEEDED for all queries.")


def main():
    parser = argparse.ArgumentParser(description="Validate grounded RAG")
    parser.add_argument(
        "--components-only",
        action="store_true",
        help="Run controlled local checks without IRIS or an LLM provider",
    )
    args = parser.parse_args()

    try:
        if args.components_only:
            validate_components()
        else:
            validate_live_generation()
    except Exception as error:
        print(f"Grounded-RAG validation FAILED: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
