"""Embed and ingest the synthetic maintenance knowledge base into IRIS."""

from src.embedding_model import embed_texts, vector_to_string
from src.iris_connection import get_connection
from src.knowledge_base import DOCUMENT_CHUNKS


def ingest_knowledge():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM SQLUser.DocumentChunk")
        existing_ids = {row[0] for row in cursor.fetchall()}
        new_chunks = [chunk for chunk in DOCUMENT_CHUNKS if chunk["id"] not in existing_ids]

        if not new_chunks:
            return 0

        embeddings = embed_texts([chunk["content"] for chunk in new_chunks])
        for chunk, embedding in zip(new_chunks, embeddings):
            # The DB-API transports the comma-separated value as a string;
            # TO_VECTOR constructs IRIS's native typed vector inside SQL.
            cursor.execute(
                """
                INSERT INTO SQLUser.DocumentChunk
                    (id, source, title, document_section, equipment_type, content, embedding)
                VALUES (?, ?, ?, ?, ?, ?, TO_VECTOR(?, FLOAT, 384))
                """,
                (
                    chunk["id"],
                    chunk["source"],
                    chunk["title"],
                    chunk["document_section"],
                    chunk["equipment_type"],
                    chunk["content"],
                    vector_to_string(embedding),
                ),
            )

        connection.commit()
        return len(new_chunks)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def main():
    try:
        inserted = ingest_knowledge()
    except Exception as error:
        print(f"Knowledge ingestion FAILED: {error}")
        return 1

    print(f"Knowledge ingestion completed successfully ({inserted} chunks inserted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
