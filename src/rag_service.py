"""Grounded maintenance assessment built on the existing hybrid retrieval."""

import json

from src.evidence_context import (
    DEFAULT_EVIDENCE_COUNT,
    format_evidence_context,
    select_evidence,
)
from src.hybrid_search import hybrid_search
from src.llm_provider import OpenAICompatibleProvider


ALLOWED_COVERAGE = {"high", "medium", "low"}
REQUIRED_FIELDS = {
    "observed_issue",
    "assessment",
    "likely_causes",
    "recommended_checks",
    "evidence_coverage",
    "limitations",
    "safety_note",
}

SYSTEM_PROMPT = """You provide industrial maintenance decision support.
Use only the supplied evidence for technical claims. Do not invent manufacturer
specifications or measurements. Do not claim inspections were performed. Do not
claim a component has failed unless the evidence supports that conclusion.
Distinguish possible causes from confirmed causes. Every likely cause and every
recommended technical check must cite at least one supplied evidence ID. If the
evidence is insufficient, say so explicitly and prefer uncertainty over an
unsupported conclusion. This is decision support, not a definitive diagnosis.
Return one valid JSON object only, with no Markdown or additional text."""

OUTPUT_SCHEMA = {
    "observed_issue": "string",
    "assessment": "string",
    "likely_causes": [{"cause": "string", "evidence_ids": ["E1"]}],
    "recommended_checks": [{"check": "string", "evidence_ids": ["E1"]}],
    "evidence_coverage": "high|medium|low",
    "limitations": ["string"],
    "safety_note": "string",
}


class GroundingValidationError(RuntimeError):
    """Raised when generated output violates the grounding contract."""


def build_user_prompt(query, selected_evidence):
    context = format_evidence_context(selected_evidence) or "No evidence available."
    return (
        f"Maintenance problem:\n{query}\n\n"
        f"Evidence note:\n{selected_evidence['context_note']}\n\n"
        f"Evidence:\n{context}\n\n"
        "Return JSON matching this schema exactly:\n"
        + json.dumps(OUTPUT_SCHEMA, indent=2)
    )


def _validate_cited_items(value, field_name, text_key, valid_evidence_ids):
    if not isinstance(value, list):
        raise GroundingValidationError(f"{field_name} must be a list")
    for position, item in enumerate(value, start=1):
        if not isinstance(item, dict) or not isinstance(item.get(text_key), str):
            raise GroundingValidationError(
                f"{field_name}[{position}] must contain a string {text_key}"
            )
        citations = item.get("evidence_ids")
        if not isinstance(citations, list) or not citations:
            raise GroundingValidationError(
                f"{field_name}[{position}] must cite at least one evidence ID"
            )
        if not all(isinstance(citation, str) for citation in citations):
            raise GroundingValidationError(
                f"{field_name}[{position}] evidence IDs must be strings"
            )
        unknown = [citation for citation in citations if citation not in valid_evidence_ids]
        if unknown:
            raise GroundingValidationError(
                f"{field_name}[{position}] cites unknown evidence: {unknown}"
            )


def parse_and_validate_output(raw_output, evidence_items):
    try:
        assessment = json.loads(raw_output)
    except json.JSONDecodeError as error:
        raise GroundingValidationError("LLM output is not valid JSON") from error
    if not isinstance(assessment, dict):
        raise GroundingValidationError("LLM output must be a JSON object")

    missing = REQUIRED_FIELDS - assessment.keys()
    if missing:
        raise GroundingValidationError(f"LLM output is missing fields: {sorted(missing)}")

    for field in ("observed_issue", "assessment", "safety_note"):
        if not isinstance(assessment[field], str):
            raise GroundingValidationError(f"{field} must be a string")
    if assessment["evidence_coverage"] not in ALLOWED_COVERAGE:
        raise GroundingValidationError("evidence_coverage must be high, medium, or low")
    if not isinstance(assessment["limitations"], list) or not all(
        isinstance(item, str) for item in assessment["limitations"]
    ):
        raise GroundingValidationError("limitations must be a list of strings")

    valid_evidence_ids = {item["evidence_id"] for item in evidence_items}
    _validate_cited_items(
        assessment["likely_causes"], "likely_causes", "cause", valid_evidence_ids
    )
    _validate_cited_items(
        assessment["recommended_checks"],
        "recommended_checks",
        "check",
        valid_evidence_ids,
    )
    return assessment


def generate_assessment(query, provider=None, evidence_count=DEFAULT_EVIDENCE_COUNT):
    provider = provider or OpenAICompatibleProvider.from_environment()
    retrieval_results = hybrid_search(query, top_k=evidence_count)
    selected = select_evidence(query, retrieval_results, evidence_count)
    raw_output = provider.generate(SYSTEM_PROMPT, build_user_prompt(query, selected))
    assessment = parse_and_validate_output(raw_output, selected["items"])
    return {
        "assessment": assessment,
        "evidence": selected["items"],
        "weak_evidence": selected["weak_evidence"],
        "context_note": selected["context_note"],
    }
