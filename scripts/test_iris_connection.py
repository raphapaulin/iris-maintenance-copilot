from getpass import getpass

import iris


def main():
    password = getpass("IRIS password: ")

    connection = iris.connect(
        "localhost:1972/MAINTENANCE",
        "_SYSTEM",
        password,
    )

    cursor = connection.cursor()

    try:
        cursor.execute("SELECT CURRENT_TIMESTAMP")
        row = cursor.fetchone()

        print("Connected to InterSystems IRIS successfully!")
        print("Namespace: MAINTENANCE")
        print(f"IRIS timestamp: {row[0]}")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
    