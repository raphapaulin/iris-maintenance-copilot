"""Create the operational maintenance tables in InterSystems IRIS."""

from src.iris_connection import get_connection


SCHEMA = "SQLUser"
LEXICAL_INDEX = "DocumentChunkContentIdx"

TABLES = {
    "Equipment": """
        CREATE TABLE SQLUser.Equipment (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            equipment_type VARCHAR(100) NOT NULL,
            manufacturer VARCHAR(200),
            model VARCHAR(100),
            location VARCHAR(200)
        )
    """,
    "MaintenanceEvent": """
        CREATE TABLE SQLUser.MaintenanceEvent (
            id INTEGER NOT NULL PRIMARY KEY,
            equipment_id INTEGER NOT NULL,
            event_date TIMESTAMP NOT NULL,
            symptom VARCHAR(1000) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            action_taken VARCHAR(2000),
            result VARCHAR(2000),
            CONSTRAINT FK_MaintenanceEvent_Equipment
                FOREIGN KEY (equipment_id) REFERENCES SQLUser.Equipment (id)
        )
    """,
    "DocumentChunk": """
        CREATE TABLE SQLUser.DocumentChunk (
            id INTEGER NOT NULL PRIMARY KEY,
            source VARCHAR(300) NOT NULL,
            title VARCHAR(300) NOT NULL,
            document_section VARCHAR(200),
            equipment_type VARCHAR(100),
            content VARCHAR(8000) NOT NULL,
            embedding VECTOR(FLOAT, 384) NOT NULL
        )
    """,
}


def table_exists(cursor, table_name):
    # IRIS exposes SQL catalog metadata through INFORMATION_SCHEMA.
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """,
        (SCHEMA, table_name),
    )
    return cursor.fetchone()[0] > 0


def index_exists(cursor, table_name, index_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.INDEXES
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND INDEX_NAME = ?
        """,
        (SCHEMA, table_name, index_name),
    )
    return cursor.fetchone()[0] > 0


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        for table_name, create_sql in TABLES.items():
            if table_exists(cursor, table_name):
                print(f"Table {SCHEMA}.{table_name} already exists; skipping.")
            else:
                cursor.execute(create_sql)
                print(f"Created table {SCHEMA}.{table_name}.")

        if index_exists(cursor, "DocumentChunk", LEXICAL_INDEX):
            print(f"Index {LEXICAL_INDEX} already exists; skipping.")
        else:
            cursor.execute(
                """
                CREATE INDEX DocumentChunkContentIdx
                ON TABLE SQLUser.DocumentChunk (content)
                AS %iFind.Index.Basic (LANGUAGE='en', LOWER=1)
                """
            )
            print(f"Created lexical index {LEXICAL_INDEX}.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def main():
    try:
        initialize_database()
    except Exception as error:
        print(f"Database initialization FAILED: {error}")
        return 1

    print("Database initialization completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
