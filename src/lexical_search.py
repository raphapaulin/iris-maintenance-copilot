"""Lexical retrieval performed with InterSystems IRIS SQL Search."""

import re

from src.iris_connection import get_connection


INDEX_NAME = "DocumentChunkContentIdx"
STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "for",
    "from",
    "in",
    "is",
    "near",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def prepare_search_terms(query):
    """Return a safe iFind OR query containing useful input terms."""
    terms = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", query.lower())
    useful_terms = list(dict.fromkeys(term for term in terms if term not in STOPWORDS))
    if not useful_terms:
        raise ValueError("Query must contain at least one searchable term")
    return " OR ".join(useful_terms)


def lexical_search(query, top_k=3):
    if not query or not query.strip():
        raise ValueError("Query text must not be empty")
    if not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer between 1 and 20")

    search_terms = prepare_search_terms(query)
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT Classname
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """,
            ("SQLUser", "DocumentChunk"),
        )
        class_row = cursor.fetchone()
        if not class_row:
            raise RuntimeError("SQLUser.DocumentChunk does not exist")
        document_chunk_class = class_row[0]

        # Both candidate matching and TF-IDF ranking execute inside IRIS.
        cursor.execute(
            f"""
            SELECT TOP {top_k}
                id, source, title, document_section, equipment_type, content,
                %iFind.Rank(
                    '%iFind.Rank.TFIDF', ?, ?, %ID, ?, 0
                ) AS lexical_score
            FROM SQLUser.DocumentChunk
            WHERE %ID %FIND search_index(DocumentChunkContentIdx, ?, 0)
            ORDER BY lexical_score DESC, id
            """,
            (document_chunk_class, INDEX_NAME, search_terms, search_terms),
        )
        return [
            {
                "id": row[0],
                "source": row[1],
                "title": row[2],
                "document_section": row[3],
                "equipment_type": row[4],
                "content": row[5],
                "lexical_score": float(row[6]),
                "lexical_rank": rank,
            }
            for rank, row in enumerate(cursor.fetchall(), start=1)
        ]
    finally:
        cursor.close()
        connection.close()
