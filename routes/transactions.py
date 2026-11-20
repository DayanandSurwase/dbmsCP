import logging
from decimal import Decimal
from flask import Blueprint, jsonify, request
from database import get_connection
from transaction_engine import execute_transfer

logger = logging.getLogger(__name__)

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api')


def _serialize_tx(row, columns):
    tx = dict(zip(columns, row))
    for k, v in tx.items():
        if isinstance(v, Decimal):
            tx[k] = str(v)
        elif hasattr(v, 'isoformat'):
            tx[k] = v.isoformat()
    return tx


@transactions_bp.route('/transactions/stats', methods=['GET'])
def transaction_stats():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT status, COUNT(*) as count,
                      COALESCE(SUM(amount), 0) as volume
               FROM transactions
               GROUP BY status"""
        )
        rows = cursor.fetchall()
        stats = {}
        total_volume = Decimal('0')
        for row in rows:
            status, count, volume = row
            stats[status] = {
                'count': int(count),
                'volume': str(volume)
            }
            total_volume += volume if volume else Decimal('0')
        cursor.close()
        return jsonify({'by_status': stats, 'total_volume': str(total_volume)})
    except Exception as exc:
        logger.error('transaction_stats error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to retrieve stats'}), 500
    finally:
        if conn:
            conn.close()


@transactions_bp.route('/transactions', methods=['POST'])
def create_transaction():
    data = request.get_json(silent=True) or {}

    # Validate required fields
    for field in ('sender_id', 'receiver_id', 'contract_id', 'amount'):
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    try:
        sender_id = int(data['sender_id'])
        receiver_id = int(data['receiver_id'])
        contract_id = int(data['contract_id'])
        amount = float(data['amount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid field types; sender_id/receiver_id/contract_id must be int, amount numeric'}), 400

    if amount <= 0:
        return jsonify({'error': 'amount must be greater than 0'}), 400
    if sender_id == receiver_id:
        return jsonify({'error': 'sender and receiver must be different accounts'}), 400

    try:
        result = execute_transfer(sender_id, receiver_id, contract_id, amount)
    except Exception as exc:
        logger.error('execute_transfer raised: %s', exc, exc_info=True)
        return jsonify({'status': 'ERROR', 'message': 'Internal error during transfer', 'transaction_id': None}), 500

    status = result.get('status', 'ERROR')
    if status == 'ERROR':
        return jsonify(result), 500
    return jsonify(result), 200


@transactions_bp.route('/transactions', methods=['GET'])
def list_transactions():
    status_filter = request.args.get('status')
    account_id_filter = request.args.get('account_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    if limit > 500:
        limit = 500

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = (
            "SELECT t.transaction_id, t.sender_id, t.receiver_id, t.contract_id, "
            "CAST(t.amount AS CHAR) as amount, t.status, t.message, t.created_at, "
            "s.account_name as sender_name, r.account_name as receiver_name, "
            "c.contract_name "
            "FROM transactions t "
            "JOIN accounts s ON t.sender_id = s.account_id "
            "JOIN accounts r ON t.receiver_id = r.account_id "
            "JOIN contracts c ON t.contract_id = c.contract_id"
        )
        conditions = []
        params = []

        if status_filter:
            conditions.append("t.status = %s")
            params.append(status_filter.upper())
        if account_id_filter is not None:
            conditions.append("(t.sender_id = %s OR t.receiver_id = %s)")
            params.extend([account_id_filter, account_id_filter])

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY t.created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(sql, params)
        columns = [d[0] for d in cursor.description]
        txs = [_serialize_tx(r, columns) for r in cursor.fetchall()]
        cursor.close()
        return jsonify(txs)
    except Exception as exc:
        logger.error('list_transactions error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to retrieve transactions'}), 500
    finally:
        if conn:
            conn.close()


@transactions_bp.route('/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT t.transaction_id, t.sender_id, t.receiver_id, t.contract_id, "
            "CAST(t.amount AS CHAR) as amount, t.status, t.message, t.created_at, "
            "s.account_name as sender_name, r.account_name as receiver_name, "
            "c.contract_name "
            "FROM transactions t "
            "JOIN accounts s ON t.sender_id = s.account_id "
            "JOIN accounts r ON t.receiver_id = r.account_id "
            "JOIN contracts c ON t.contract_id = c.contract_id "
            "WHERE t.transaction_id = %s",
            (transaction_id,)
        )
        columns = [d[0] for d in cursor.description]
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({'error': 'Transaction not found'}), 404
        tx = _serialize_tx(row, columns)

        # Audit log
        cursor.execute(
            "SELECT log_id, action, details, created_at "
            "FROM audit_logs WHERE transaction_id = %s ORDER BY created_at ASC",
            (transaction_id,)
        )
        log_cols = [d[0] for d in cursor.description]
        logs = []
        for r in cursor.fetchall():
            entry = dict(zip(log_cols, r))
            if entry.get('created_at') and hasattr(entry['created_at'], 'isoformat'):
                entry['created_at'] = entry['created_at'].isoformat()
            logs.append(entry)
        cursor.close()

        tx['audit_logs'] = logs
        return jsonify(tx)
    except Exception as exc:
        logger.error('get_transaction error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to retrieve transaction'}), 500
    finally:
        if conn:
            conn.close()
