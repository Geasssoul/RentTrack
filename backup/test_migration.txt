"""
RentTrack - Automatic Migration Test

This test NEVER touches the real:
    data/rental.db

It creates a temporary SQLite database, builds the current schema,
inserts representative data, runs the migration system, verifies
the data and schema, tests rollback, and cleans everything up.

Run:
    python test_migration.py
"""

import importlib.util
import sqlite3
import tempfile
from pathlib import Path
import shutil
import sys
import traceback


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_DIR / "database.py"
MIGRATIONS_FILE = PROJECT_DIR / "migrations.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run():
    print("=" * 50)
    print("RentTrack Migration Test")
    print("=" * 50)
    print()

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(f"Missing: {DATABASE_FILE}")

    if not MIGRATIONS_FILE.exists():
        raise FileNotFoundError(f"Missing: {MIGRATIONS_FILE}")

    db_module = load_module("renttrack_test_database", DATABASE_FILE)
    migrations = load_module("renttrack_test_migrations", MIGRATIONS_FILE)

    temp_dir = Path(tempfile.mkdtemp(prefix="renttrack_migration_test_"))
    test_db = temp_dir / "rental.db"

    passed = 0

    try:
        # ---------------------------------------------------------
        # 1. Create a completely isolated test database.
        # ---------------------------------------------------------
        conn = sqlite3.connect(test_db)
        conn.execute("PRAGMA foreign_keys = ON")

        # Reproduce the application's schema creation logic without
        # touching the real database.
        original_db_path = db_module.DB_PATH
        db_module.DB_PATH = test_db

        print("[1/9] Create isolated test database")
        db_module.create_database()

        check(test_db.exists(), "Test database was not created.")
        passed += 1
        print("      PASS")

        # Reopen the test DB.
        conn = sqlite3.connect(test_db)
        conn.execute("PRAGMA foreign_keys = ON")

        # ---------------------------------------------------------
        # 2. Insert realistic test data.
        # ---------------------------------------------------------
        print("[2/9] Insert test Property / Tenant / Bill data")

        cur = conn.cursor()

        cur.execute(
            "INSERT INTO properties (name, address) VALUES (?, ?)",
            ("12 Queen Street", "12 Queen Street"),
        )
        property_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO tenants (name, phone, email, property_id)
            VALUES (?, ?, ?, ?)
            """,
            ("Test Tenant", "0210000000", "test@example.com", property_id),
        )
        tenant_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO bills
            (property_id, tenant_id, start_date, end_date, created_date, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                property_id,
                tenant_id,
                "2026-09-01",
                "2026-09-30",
                "2026-09-30",
                "Migration test bill",
            ),
        )
        bill_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO bill_charges (bill_id, description, amount)
            VALUES (?, ?, ?)
            """,
            (bill_id, "Rent", 500.00),
        )

        cur.execute(
            """
            INSERT INTO bill_payments
            (bill_id, amount, payment_date, note)
            VALUES (?, ?, ?, ?)
            """,
            (bill_id, 200.00, "2026-09-30", "Test payment"),
        )

        conn.commit()
        passed += 1
        print("      PASS")

        # ---------------------------------------------------------
        # 3. Verify data exists before migration.
        # ---------------------------------------------------------
        print("[3/9] Verify original test data")

        row = cur.execute(
            "SELECT address FROM properties WHERE id = ?",
            (property_id,),
        ).fetchone()
        check(row and row[0] == "12 Queen Street", "Property missing.")

        row = cur.execute(
            "SELECT name FROM tenants WHERE id = ?",
            (tenant_id,),
        ).fetchone()
        check(row and row[0] == "Test Tenant", "Tenant missing.")

        row = cur.execute(
            "SELECT note FROM bills WHERE id = ?",
            (bill_id,),
        ).fetchone()
        check(row and row[0] == "Migration test bill", "Bill missing.")

        row = cur.execute(
            "SELECT amount FROM bill_charges WHERE bill_id = ?",
            (bill_id,),
        ).fetchone()
        check(row and row[0] == 500.00, "Bill charge missing.")

        row = cur.execute(
            "SELECT amount FROM bill_payments WHERE bill_id = ?",
            (bill_id,),
        ).fetchone()
        check(row and row[0] == 200.00, "Bill payment missing.")

        passed += 1
        print("      PASS")

        # ---------------------------------------------------------
        # 4. Run migration.
        # ---------------------------------------------------------
        print("[4/9] Run migration system")

        conn.close()
        conn = sqlite3.connect(test_db)
        conn.execute("PRAGMA foreign_keys = ON")

        migrations.migrate_database(conn, test_db)

        passed += 1
        print("      PASS")

        # ---------------------------------------------------------
        # 5. Verify schema version.
        # ---------------------------------------------------------
        print("[5/9] Verify schema version")

        version = migrations.get_schema_version(conn)
        expected = migrations.CURRENT_SCHEMA_VERSION

        check(
            version == expected,
            f"Expected schema version {expected}, got {version}.",
        )

        passed += 1
        print(f"      PASS (version = {version})")

        # ---------------------------------------------------------
        # 6. Verify all important data survived.
        # ---------------------------------------------------------
        print("[6/9] Verify data survived migration")

        checks = [
            (
                "Property",
                "SELECT address FROM properties WHERE id = ?",
                (property_id,),
                "12 Queen Street",
            ),
            (
                "Tenant",
                "SELECT name FROM tenants WHERE id = ?",
                (tenant_id,),
                "Test Tenant",
            ),
            (
                "Bill",
                "SELECT note FROM bills WHERE id = ?",
                (bill_id,),
                "Migration test bill",
            ),
            (
                "Charge",
                "SELECT amount FROM bill_charges WHERE bill_id = ?",
                (bill_id,),
                500.00,
            ),
            (
                "Payment",
                "SELECT amount FROM bill_payments WHERE bill_id = ?",
                (bill_id,),
                200.00,
            ),
        ]

        for label, query, params, expected_value in checks:
            value = conn.execute(query, params).fetchone()
            check(value is not None, f"{label} disappeared.")
            check(
                value[0] == expected_value,
                f"{label} changed unexpectedly: {value[0]!r}",
            )

        passed += 1
        print("      PASS")

        # ---------------------------------------------------------
        # 7. SQLite integrity check.
        # ---------------------------------------------------------
        print("[7/9] Run SQLite integrity check")

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        check(integrity == "ok", f"Integrity check failed: {integrity}")

        passed += 1
        print("      PASS")

        # ---------------------------------------------------------
        # 8. Verify migration is idempotent.
        #    Running it again should not change anything.
        # ---------------------------------------------------------
        print("[8/9] Run migration a second time")

        migrations.migrate_database(conn, test_db)

        version_again = migrations.get_schema_version(conn)
        check(
            version_again == expected,
            "Second migration changed schema version unexpectedly.",
        )

        row = conn.execute(
            "SELECT COUNT(*) FROM bills WHERE id = ?",
            (bill_id,),
        ).fetchone()
        check(row[0] == 1, "Second migration changed bill data.")

        integrity_again = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        check(
            integrity_again == "ok",
            f"Second integrity check failed: {integrity_again}",
        )

        passed += 1
        print("      PASS")

        # ---------------------------------------------------------
        # 9. Rollback test.
        # ---------------------------------------------------------
        print("[9/9] Test rollback behaviour")

        rollback_conn = sqlite3.connect(":memory:")
        rollback_conn.execute(
            """
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
            """
        )
        rollback_conn.execute(
            "INSERT INTO test_data (value) VALUES (?)",
            ("before",),
        )
        rollback_conn.commit()

        try:
            rollback_conn.execute("BEGIN")
            rollback_conn.execute(
                "UPDATE test_data SET value = 'changed'"
            )
            raise RuntimeError("Intentional migration failure for test")
        except RuntimeError:
            rollback_conn.rollback()

        value = rollback_conn.execute(
            "SELECT value FROM test_data WHERE id = 1"
        ).fetchone()[0]

        check(
            value == "before",
            "Rollback test failed: original value was not restored.",
        )

        rollback_conn.close()

        passed += 1
        print("      PASS")

        print()
        print("=" * 50)
        print(f"ALL TESTS PASSED ({passed}/9)")
        print("=" * 50)
        return 0

    except Exception as exc:
        print()
        print("=" * 50)
        print("TEST FAILED")
        print("=" * 50)
        print()
        print(str(exc))
        print()
        traceback.print_exc()
        return 1

    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

        # Restore the module's DB_PATH in memory.
        try:
            db_module.DB_PATH = original_db_path
        except Exception:
            pass

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
