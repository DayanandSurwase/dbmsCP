import logging
from decimal import Decimal
from flask import Blueprint, jsonify, request
from database import get_connection

logger = logging.getLogger(__name__)

accounts_bp = Blueprint('accounts', __name__, url_prefix='/api')


def _account_row(row, columns):
    acc = dict(zip(columns, row))
    if isinstance(acc.get('balance'), Decimal):
        acc['balance'] = str(acc['balance'])
    if acc.get('created_at') and hasattr(acc['created_at'], 'isoformat'):
        acc['created_at'] = acc['created_at'].isoformat()
    return acc


def _tx_row(row, columns):
    tx = dict(zip(columns, row))
    for k, v in tx.items():
        if isinstance(v, Decimal):
            tx[k] = str(v)
        elif hasattr(v, 'isoformat'):
            tx[k] = v.isoformat()
    return tx


@accounts_bp.route('/accounts', methods=['GET'])
def list_accounts():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_id, account_name, CAST(balance AS CHAR) as balance, created_at "
            "FROM accounts ORDER BY account_id"
        )
        columns = [d[0] for d in cursor.description]
        accounts = [_account_row(r, columns) for r in cursor.fetchall()]
        cursor.close()
        return jsonify(accounts)
    except Exception as exc:
        logger.error('list_accounts error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to retrieve accounts'}), 500
    finally:
        if conn:
            conn.close()


@accounts_bp.route('/accounts', methods=['POST'])
def create_account():
    data = request.get_json(silent=True) or {}
    account_name = data.get('account_name', '').strip()
    if not account_name:
        return jsonify({'error': 'account_name is required and must be non-empty'}), 400

    # Support either initial_balance or balance from the request payload
    balance_val = data.get('initial_balance', data.get('balance', 0))
    try:
        initial_balance = float(balance_val)
    except (TypeError, ValueError):
        return jsonify({'error': 'initial_balance must be a valid number'}), 400
    if initial_balance < 0:
        return jsonify({'error': 'initial_balance must be >= 0'}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if an account with this name already exists
        cursor.execute("SELECT account_id FROM accounts WHERE LOWER(account_name) = LOWER(%s)", (account_name,))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            return jsonify({'error': f"An account with the name '{account_name}' already exists. Users can only open 1 account."}), 400

        cursor.execute(
            "INSERT INTO accounts (account_name, balance) VALUES (%s, %s)",
            (account_name, initial_balance)
        )
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute(
            "SELECT account_id, account_name, CAST(balance AS CHAR) as balance, created_at "
            "FROM accounts WHERE account_id = %s",
            (new_id,)
        )
        columns = [d[0] for d in cursor.description]
        acc = _account_row(cursor.fetchone(), columns)
        cursor.close()
        return jsonify(acc), 201
    except Exception as exc:
        if conn:
            conn.rollback()
        err_msg = str(exc).lower()
        if 'duplicate' in err_msg or 'unique' in err_msg:
            return jsonify({'error': f"An account with the name '{account_name}' already exists."}), 400
        logger.error('create_account error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to create account'}), 500
    finally:
        if conn:
            conn.close()


@accounts_bp.route('/accounts/<int:account_id>', methods=['GET'])
def get_account(account_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT account_id, account_name, CAST(balance AS CHAR) as balance, created_at "
            "FROM accounts WHERE account_id = %s",
            (account_id,)
        )
        columns = [d[0] for d in cursor.description]
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({'error': 'Account not found'}), 404
        acc = _account_row(row, columns)

        # Recent transactions (last 10)
        cursor.execute(
            """SELECT t.transaction_id, t.sender_id, t.receiver_id, t.contract_id,
                      CAST(t.amount AS CHAR) as amount, t.status, t.message, t.created_at,
                      s.account_name as sender_name, r.account_name as receiver_name,
                      c.contract_name
               FROM transactions t
               JOIN accounts s ON t.sender_id = s.account_id
               JOIN accounts r ON t.receiver_id = r.account_id
               JOIN contracts c ON t.contract_id = c.contract_id
               WHERE t.sender_id = %s OR t.receiver_id = %s
               ORDER BY t.created_at DESC
               LIMIT 10""",
            (account_id, account_id)
        )
        tx_columns = [d[0] for d in cursor.description]
        transactions = [_tx_row(r, tx_columns) for r in cursor.fetchall()]
        cursor.close()

        acc['recent_transactions'] = transactions
        return jsonify(acc)
    except Exception as exc:
        logger.error('get_account error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to retrieve account'}), 500
    finally:
        if conn:
            conn.close()
