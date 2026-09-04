"""Validate the operational maintenance data stored in IRIS."""

from src.iris_connection import get_connection


def validate_database():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, name, equipment_type, manufacturer, model, location
            FROM SQLUser.Equipment
            ORDER BY id
            """
        )
        equipment_rows = cursor.fetchall()

        print("\nEquipment")
        print("---------")
        for row in equipment_rows:
            print(f"{row[0]}: {row[1]} | {row[2]} | {row[5]}")

        cursor.execute(
            """
            SELECT e.name, m.event_date, m.symptom, m.severity,
                   m.action_taken, m.result
            FROM SQLUser.Equipment e
            INNER JOIN SQLUser.MaintenanceEvent m ON m.equipment_id = e.id
            ORDER BY m.event_date, m.id
            """
        )
        event_rows = cursor.fetchall()

        print("\nMaintenance history")
        print("-------------------")
        for row in event_rows:
            print(f"{row[1]} | {row[0]} | {row[3]}")
            print(f"  Symptom: {row[2]}")
            print(f"  Action: {row[4] or '-'}")
            print(f"  Result: {row[5] or '-'}")

        if not equipment_rows or not event_rows:
            raise RuntimeError("validation queries returned no data")
    finally:
        cursor.close()
        connection.close()


def main():
    try:
        validate_database()
    except Exception as error:
        print(f"\nValidation FAILED: {error}")
        return 1

    print("\nValidation SUCCEEDED: equipment and joined maintenance events were read from IRIS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
