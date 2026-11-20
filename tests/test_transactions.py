"""
tests/test_transactions.py
Unit tests for execute_transfer() against the TEST database.
Each test runs in an isolated, clean state via setUp/tearDown.
"""

import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path

# Ensure the project root is on sys.path so imports work when run from any cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_TEST_NAME
from database import get_connection
from transaction_engine import execute_transfer


def _run_schema_on_test_db(conn):
    """
    Create all tables in the test DB.
    We read schema.sql but skip the CREATE DATABASE / USE lines because
    we are already connected to conditional_engine_test.
    """
    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    sql_text = schema_path.read_text(encoding="utf-8")

    # Clean SQL: remove comment-only lines and strip CREATE DATABASE / USE
    cleaned_lines = []
    for line in sql_text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("--"):
            continue
        cleaned_lines.append(line)
    clean_sql = "\n".join(cleaned_lines)

    filtered_statements = []
    for raw_stmt in clean_sql.split(";"):
        stmt = raw_stmt.strip()
        if not stmt:
            continue
        upper_stmt = stmt.upper()
        if "CREATE DATABASE" in upper_stmt or upper_stmt.startswith("USE "):
            continue
        filtered_statements.append(stmt)

    cursor = conn.cursor()
    for stmt in filtered_statements:
        try:
            cursor.execute(stmt)
            conn.commit()
        except Exception as exc:
            err_msg = str(exc).lower()
            if "duplicate key name" in err_msg or "already exists" in err_msg:
                conn.rollback()
            else:
                conn.rollback()
                raise
    cursor.close()


class TestExecuteTransfer(unittest.TestCase):
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setUp(self):
        """Connect to test DB, build schema, insert fresh fixtures."""
        self.conn = get_connection(DB_TEST_NAME)
        _run_schema_on_test_db(self.conn)

        cur = self.conn.cursor()

        # Insert Alice
        cur.execute(
            "INSERT INTO accounts (account_name, balance) VALUES (%s, %s)",
            ("Alice", "5000.00"),
        )
        self.alice_id = cur.lastrowid

        # Insert Bob
        cur.execute(
            "INSERT INTO accounts (account_name, balance) VALUES (%s, %s)",
            ("Bob", "2000.00"),
        )
        self.bob_id = cur.lastrowid

        # Insert Contract: min_sender_balance=1000, max_transfer_amount=5000, active
        cur.execute(
            """INSERT INTO contracts
               (contract_name, description, min_sender_balance, max_transfer_amount, is_active)
               VALUES (%s, %s, %s, %s, %s)""",
            ("Test Contract", "Standard test contract", "1000.00", "5000.00", True),
        )
        self.contract_id = cur.lastrowid

        self.conn.commit()
        cur.close()

    def tearDown(self):
        """Truncate all tables and close connection."""
        cur = self.conn.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for table in ("audit_logs", "transactions", "contract_conditions", "contracts", "accounts"):
            cur.execute(f"TRUNCATE TABLE {table}")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        self.conn.commit()
        cur.close()
        self.conn.close()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _get_balance(self, account_id):
        conn = get_connection(DB_TEST_NAME)
        cur = conn.cursor()
        cur.execute("SELECT balance FROM accounts WHERE account_id=%s", (account_id,))
        bal = cur.fetchone()[0]
        cur.close()
        conn.close()
        return Decimal(str(bal))

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_successful_transfer(self):
        """Alice sends 1000 to Bob — should SUCCESS, balances updated."""
        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 1000, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(self._get_balance(self.alice_id), Decimal("4000.00"))
        self.assertEqual(self._get_balance(self.bob_id), Decimal("3000.00"))

    def test_02_exceeds_contract_limit(self):
        """Alice tries 10000 — exceeds max_transfer_amount=5000."""
        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 10000, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("limit", result["message"].lower())
        # Balances must be unchanged
        self.assertEqual(self._get_balance(self.alice_id), Decimal("5000.00"))
        self.assertEqual(self._get_balance(self.bob_id), Decimal("2000.00"))

    def test_03_min_sender_balance_violated(self):
        """Alice=5000. Sending 4500 leaves 500 < min_balance=1000 → REJECTED."""
        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 4500, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("minimum", result["message"].lower())

    def test_04_insufficient_balance(self):
        """Bob has 2000. Bob tries sending 3000 → REJECTED (insufficient)."""
        result = execute_transfer(
            self.bob_id, self.alice_id, self.contract_id, 3000, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("insufficient", result["message"].lower())

    def test_05_inactive_contract(self):
        """Deactivate contract, then try transfer → REJECTED (not active)."""
        conn = get_connection(DB_TEST_NAME)
        cur = conn.cursor()
        cur.execute(
            "UPDATE contracts SET is_active=FALSE WHERE contract_id=%s",
            (self.contract_id,),
        )
        conn.commit()
        cur.close()
        conn.close()

        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 1000, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("active", result["message"].lower())

    def test_06_same_sender_receiver(self):
        """Sender == Receiver → REJECTED (pre-DB validation)."""
        result = execute_transfer(
            self.alice_id, self.alice_id, self.contract_id, 100, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")

    def test_07_zero_amount(self):
        """Amount = 0 → REJECTED."""
        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 0, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")

    def test_08_negative_amount(self):
        """Amount < 0 → REJECTED."""
        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, -500, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")

    def test_09_nonexistent_account(self):
        """sender_id=9999 doesn't exist → ERROR."""
        result = execute_transfer(
            9999, self.bob_id, self.contract_id, 100, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "ERROR")

    def test_10_nonexistent_contract(self):
        """contract_id=9999 doesn't exist → ERROR."""
        result = execute_transfer(
            self.alice_id, self.bob_id, 9999, 100, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "ERROR")

    def test_11_atomicity_rollback(self):
        """A REJECTED transfer must NOT change any balance."""
        before_alice = self._get_balance(self.alice_id)
        before_bob = self._get_balance(self.bob_id)

        result = execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 10000, db_name=DB_TEST_NAME
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self._get_balance(self.alice_id), before_alice)
        self.assertEqual(self._get_balance(self.bob_id), before_bob)

    def test_12_transaction_recorded_in_history(self):
        """Both SUCCESS and REJECTED transactions appear in the transactions table."""
        execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 1000, db_name=DB_TEST_NAME
        )
        execute_transfer(
            self.alice_id, self.bob_id, self.contract_id, 10000, db_name=DB_TEST_NAME
        )

        conn = get_connection(DB_TEST_NAME)
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT status FROM transactions ORDER BY transaction_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        statuses = [r["status"] for r in rows]
        self.assertIn("SUCCESS", statuses)
        self.assertIn("REJECTED", statuses)

    def test_13_concurrent_no_negative_balance(self):
        """
        Two threads both try to drain Alice simultaneously.
        Balance must never go negative; at most one succeeds.
        Alice=5000, min_balance=1000 → max send = 4000.
        Two sends of 3000 would total 6000 > 4000, so only one can succeed.
        """
        import threading

        results = []
        lock = threading.Lock()

        def transfer():
            r = execute_transfer(
                self.alice_id, self.bob_id, self.contract_id, 3000, db_name=DB_TEST_NAME
            )
            with lock:
                results.append(r)

        threads = [threading.Thread(target=transfer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r["status"] == "SUCCESS")
        self.assertLessEqual(success_count, 1, "At most one concurrent transfer should succeed")

        final_balance = self._get_balance(self.alice_id)
        self.assertGreaterEqual(final_balance, Decimal("0"), "Balance must never go negative")


if __name__ == "__main__":
    unittest.main()
