"""Semantic retrieval performed with InterSystems IRIS Vector Search."""

from src.embedding_model import embed_text, vector_to_string
from src.iris_connection import get_connection


def semantic_search(query, top_k=3):
    if not query or not query.strip():
        raise ValueError("Query text must not be empty")
    if not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer between 1 and 20")

    query_vector = vector_to_string(embed_text(query))
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # VECTOR_COSINE is evaluated and sorted by IRIS, not by Python.
        cursor.execute(
            f"""
            SELECT TOP {top_k}
                id, source, title, document_section, equipment_type, content,
                VECTOR_COSINE(embedding, TO_VECTOR(?, FLOAT, 384)) AS similarity
            FROM SQLUser.DocumentChunk
            ORDER BY similarity DESC
            """,
            (query_vector,),
        )
        return [
            {
                "id": row[0],
                "source": row[1],
                "title": row[2],
                "document_section": row[3],
                "equipment_type": row[4],
                "content": row[5],
                "similarity": float(row[6]),
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        connection.close()
