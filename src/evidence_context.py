"""Select hybrid results and build deterministic grounded-LLM context."""

import re


DEFAULT_EVIDENCE_COUNT = 3


def _query_identifiers(query):
    """Extract code-like identifiers such as ZX-991 without domain assumptions."""
    candidates = re.findall(r"\b[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+\b", query)
    return [
        value
        for value in candidates
        if any(char.isalpha() for char in value)
        and any(char.isdigit() for char in value)
    ]


def select_evidence(query, hybrid_results, max_evidence=DEFAULT_EVIDENCE_COUNT):
    if not isinstance(max_evidence, int) or max_evidence < 1:
        raise ValueError("max_evidence must be a positive integer")

    evidence = []
    for position, result in enumerate(hybrid_results[:max_evidence], start=1):
        evidence.append(
            {
                "evidence_id": f"E{position}",
                "chunk_id": result["id"],
                "source": result["source"],
                "title": result["title"],
                "document_section": result["document_section"],
                "equipment_type": result["equipment_type"],
                "content": result["content"],
                "rrf_score": result["rrf_score"],
                "semantic_rank": result.get("semantic_rank"),
                "semantic_score": result.get("semantic_score"),
                "lexical_rank": result.get("lexical_rank"),
                "lexical_score": result.get("lexical_score"),
            }
        )

    combined_content = " ".join(item["content"] for item in evidence).lower()
    missing_identifiers = [
        value for value in _query_identifiers(query) if value.lower() not in combined_content
    ]
    has_cross_signal_evidence = any(
        item["semantic_rank"] is not None and item["lexical_rank"] is not None
        for item in evidence
    )
    weak_evidence = not evidence or not has_cross_signal_evidence or bool(missing_identifiers)

    notes = ["The evidence is synthetic, general guidance and may be incomplete."]
    if not has_cross_signal_evidence:
        notes.append("No selected chunk was supported by both retrieval rankings.")
    if missing_identifiers:
        notes.append(
            "These query identifiers do not appear in the evidence: "
            + ", ".join(missing_identifiers)
            + ". Do not infer their meaning."
        )
    if not evidence:
        notes.append("No evidence chunks were available.")

    return {
        "items": evidence,
        "weak_evidence": weak_evidence,
        "context_note": " ".join(notes),
    }


def format_evidence_context(selected_evidence):
    blocks = []
    for item in selected_evidence["items"]:
        blocks.append(
            "\n".join(
                [
                    f"[{item['evidence_id']}]",
                    f"DocumentChunk ID: {item['chunk_id']}",
                    f"Title: {item['title']}",
                    f"Source: {item['source']}",
                    f"Document section: {item['document_section'] or '-'}",
                    f"Equipment type: {item['equipment_type'] or '-'}",
                    f"Content: {item['content']}",
                ]
            )
        )
    return "\n\n".join(blocks)
