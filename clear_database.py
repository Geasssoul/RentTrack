import sqlite3
from pathlib import Path

# RentTrack database location
DB_PATH = Path(__file__).resolve().parent / "data" / "rental.db"


def clear_database():
    if not DB_PATH.exists():
        print(f"Database not found:\n{DB_PATH}")
        return

    print("WARNING: This will permanently delete all RentTrack data.")
    print("The database tables and structure will be kept.")
    print()
    print(f"Database: {DB_PATH}")
    print()

    confirmation = input(
        "Type CLEAR to permanently delete all data: "
    ).strip()

    if confirmation != "CLEAR":
        print("Cancelled. No data was changed.")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Delete child tables first so this also works with older
        # databases where some foreign-key cascades may not exist.
        tables = [
            "bill_payments",
            "bill_charges",
            "bills",
            "allocations",
            "charges",
            "payments",
            "billing_periods",
            "rent_agreements",
            "tenants",
            "properties",
        ]

        for table in tables:
            cursor.execute(f"DELETE FROM {table}")

        # Reset AUTOINCREMENT counters where the table exists.
        # This makes the next Property/Tenant/Bill start again from ID 1.
        for table in tables:
            try:
                cursor.execute(
                    "DELETE FROM sqlite_sequence WHERE name = ?",
                    (table,),
                )
            except sqlite3.OperationalError:
                pass

        conn.commit()

        print()
        print("Database cleared successfully.")
        print("All data has been removed.")
        print("Table structures have been kept.")
        print("IDs will start again from 1 for new records.")

    except Exception as e:
        conn.rollback()
        print()
        print("ERROR: Database was not cleared.")
        print(e)

    finally:
        conn.close()


if __name__ == "__main__":
    clear_database()
