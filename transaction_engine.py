from decimal import Decimal
from database import get_connection


def execute_transfer(sender_id, receiver_id, contract_id, amount, db_name=None):
    """
    Execute a conditional transfer between two accounts.

    Returns a dict with keys:
        status          – 'SUCCESS' | 'REJECTED' | 'ERROR'
        message         – human-readable explanation
        transaction_id  – integer PK if a row was written, else None

    ACID properties enforced:
        Atomicity   – debit + credit + audit log commit together or rollback
        Consistency – CHECK constraints + FK + contract rules evaluated in Python
        Isolation   – SELECT FOR UPDATE locks rows (REPEATABLE READ default)
        Durability  – InnoDB COMMIT
    """
    amount = Decimal(str(amount))

    # --- Basic input validation (pre-DB) ---
    if amount <= Decimal('0'):
        return {
            "status": "REJECTED",
            "message": "Amount must be greater than zero",
            "transaction_id": None,
        }
    if sender_id == receiver_id:
        return {
            "status": "REJECTED",
            "message": "Sender and receiver must be different accounts",
            "transaction_id": None,
        }

    conn = get_connection(db_name)
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        # Lock both account rows in consistent ID order to prevent deadlocks
        low_id, high_id = sorted([sender_id, receiver_id])
        cursor.execute(
            """
            SELECT account_id, account_name, balance
            FROM accounts
            WHERE account_id IN (%s, %s)
            ORDER BY account_id
            FOR UPDATE
            """,
            (low_id, high_id),
        )
        rows = cursor.fetchall()
        accounts = {row["account_id"]: row for row in rows}

        if sender_id not in accounts:
            raise ValueError(f"Sender account {sender_id} does not exist")
        if receiver_id not in accounts:
            raise ValueError(f"Receiver account {receiver_id} does not exist")

        # Lock contract row
        cursor.execute(
            """
            SELECT contract_id, contract_name, min_sender_balance,
                   max_transfer_amount, is_active
            FROM contracts
            WHERE contract_id = %s
            FOR UPDATE
            """,
            (contract_id,),
        )
        contract = cursor.fetchone()

        if not contract:
            raise ValueError(f"Contract {contract_id} does not exist")

        sender = accounts[sender_id]
        sender_balance = Decimal(str(sender["balance"]))
        min_balance = Decimal(str(contract["min_sender_balance"]))
        max_amount = Decimal(str(contract["max_transfer_amount"]))

        # --- Contract condition checks ---
        rejection_reason = None
        if not contract["is_active"]:
            rejection_reason = "Contract is not active"
        elif amount > max_amount:
            rejection_reason = (
                f"Transfer amount exceeds contract limit of \u20b9{max_amount:,.2f}"
            )
        elif sender_balance < amount:
            rejection_reason = (
                f"Insufficient balance (available: \u20b9{sender_balance:,.2f})"
            )
        elif sender_balance - amount < min_balance:
            rejection_reason = (
                f"Minimum sender balance condition violated "
                f"(must retain \u20b9{min_balance:,.2f})"
            )

        if rejection_reason:
            # Nothing to undo in the main transaction; rollback for a clean slate
            conn.rollback()

            # Record rejection in a fresh transaction so it is always persisted
            conn.start_transaction()
            cursor.execute(
                """
                INSERT INTO transactions
                    (sender_id, receiver_id, contract_id, amount, status, message)
                VALUES (%s, %s, %s, %s, 'REJECTED', %s)
                """,
                (sender_id, receiver_id, contract_id, str(amount), rejection_reason),
            )
            txn_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO audit_logs (transaction_id, action, details)
                VALUES (%s, 'TRANSACTION_REJECTED', %s)
                """,
                (
                    txn_id,
                    f"Rejected: {rejection_reason} | "
                    f"Sender: {sender['account_name']} | Amount: {amount}",
                ),
            )
            conn.commit()
            return {
                "status": "REJECTED",
                "message": rejection_reason,
                "transaction_id": txn_id,
            }

        # --- Execute transfer atomically ---
        cursor.execute(
            "UPDATE accounts SET balance = balance - %s WHERE account_id = %s",
            (str(amount), sender_id),
        )
        cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE account_id = %s",
            (str(amount), receiver_id),
        )

        success_msg = (
            f"Transfer of \u20b9{amount:,.2f} from "
            f"{sender['account_name']} to "
            f"{accounts[receiver_id]['account_name']} completed"
        )
        cursor.execute(
            """
            INSERT INTO transactions
                (sender_id, receiver_id, contract_id, amount, status, message)
            VALUES (%s, %s, %s, %s, 'SUCCESS', %s)
            """,
            (sender_id, receiver_id, contract_id, str(amount), success_msg),
        )
        txn_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO audit_logs (transaction_id, action, details)
            VALUES (%s, 'TRANSACTION_SUCCESS', %s)
            """,
            (
                txn_id,
                f"Success | Sender: {sender['account_name']} | "
                f"Receiver: {accounts[receiver_id]['account_name']} | "
                f"Amount: {amount} | Contract: {contract['contract_name']}",
            ),
        )

        conn.commit()  # Atomicity: all above committed together

        return {"status": "SUCCESS", "message": success_msg, "transaction_id": txn_id}

    except ValueError as ve:
        conn.rollback()
        return {"status": "ERROR", "message": str(ve), "transaction_id": None}

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {
            "status": "ERROR",
            "message": "An unexpected database error occurred",
            "transaction_id": None,
        }

    finally:
        cursor.close()
        conn.close()
