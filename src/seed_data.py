"""Insert a small synthetic industrial-maintenance data set."""

from src.iris_connection import get_connection


EQUIPMENT = [
    (1, "Main Conveyor Motor", "Electric motor", "WEG", "W22", "Assembly Line A"),
    (2, "Cooling Water Pump", "Centrifugal pump", "KSB", "Etanorm 050-032-160", "Utility Room"),
    (3, "Exhaust Fan 01", "Industrial fan", None, None, "Paint Booth"),
]

MAINTENANCE_EVENTS = [
    (1, 1, "2026-07-03 08:30:00", "High vibration at the drive-end bearing", "High", "Replaced the bearing and aligned the coupling", "Vibration returned to normal range"),
    (2, 1, "2026-08-12 14:15:00", "Bearing temperature rise during peak load", "Medium", "Cleaned cooling fins and checked lubrication", "Temperature stabilized at 68 C"),
    (3, 2, "2026-06-21 10:00:00", "Cavitation noise and unstable discharge pressure", "High", "Cleaned suction strainer and opened inlet valve fully", "Stable pressure and no cavitation detected"),
    (4, 2, "2026-08-25 16:40:00", "Minor seal leakage", "Low", "Adjusted mechanical seal and monitored leakage", "Leakage stopped"),
    (5, 3, "2026-07-29 11:20:00", "Abnormal noise and increased vibration", "Medium", "Removed blade buildup and balanced the rotor", "Noise and vibration reduced"),
]


def insert_if_missing(cursor, table_name, columns, row):
    cursor.execute(f"SELECT COUNT(*) FROM SQLUser.{table_name} WHERE id = ?", (row[0],))
    if cursor.fetchone()[0] > 0:
        return False

    placeholders = ", ".join("?" for _ in row)
    column_list = ", ".join(columns)
    cursor.execute(
        f"INSERT INTO SQLUser.{table_name} ({column_list}) VALUES ({placeholders})",
        row,
    )
    return True


def seed_database():
    connection = get_connection()
    cursor = connection.cursor()
    inserted = 0

    try:
        for row in EQUIPMENT:
            inserted += insert_if_missing(
                cursor,
                "Equipment",
                ("id", "name", "equipment_type", "manufacturer", "model", "location"),
                row,
            )

        for row in MAINTENANCE_EVENTS:
            inserted += insert_if_missing(
                cursor,
                "MaintenanceEvent",
                ("id", "equipment_id", "event_date", "symptom", "severity", "action_taken", "result"),
                row,
            )

        connection.commit()
        return inserted
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def main():
    try:
        inserted = seed_database()
    except Exception as error:
        print(f"Database seeding FAILED: {error}")
        return 1

    print(f"Database seeding completed successfully ({inserted} rows inserted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
