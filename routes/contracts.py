import logging
from decimal import Decimal
from flask import Blueprint, jsonify, request
from database import get_connection

logger = logging.getLogger(__name__)

contracts_bp = Blueprint('contracts', __name__, url_prefix='/api')


def _serialize_contract(row, columns):
    c = dict(zip(columns, row))
    for k, v in c.items():
        if isinstance(v, Decimal):
            c[k] = str(v)
        elif hasattr(v, 'isoformat'):
            c[k] = v.isoformat()
    # is_active comes back as int (0/1) from MySQL, cast to bool
    if 'is_active' in c:
        c['is_active'] = bool(c['is_active'])
    return c


@contracts_bp.route('/contracts', methods=['GET'])
def list_contracts():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT contract_id, contract_name, description, "
            "CAST(min_sender_balance AS CHAR) as min_sender_balance, "
            "CAST(max_transfer_amount AS CHAR) as max_transfer_amount, "
            "is_active, created_at FROM contracts ORDER BY contract_id"
        )
        columns = [d[0] for d in cursor.description]
        contracts = []
        for row in cursor.fetchall():
            c = _serialize_contract(row, columns)
            # Fetch conditions
            cursor2 = conn.cursor()
            cursor2.execute(
                "SELECT condition_id, condition_type, "
                "CAST(condition_value AS CHAR) as condition_value, description "
                "FROM contract_conditions WHERE contract_id = %s",
                (c['contract_id'],)
            )
            cond_cols = [d[0] for d in cursor2.description]
            c['conditions'] = [dict(zip(cond_cols, r)) for r in cursor2.fetchall()]
            cursor2.close()
            contracts.append(c)
        cursor.close()
        return jsonify(contracts)
    except Exception as exc:
        logger.error('list_contracts error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to retrieve contracts'}), 500
    finally:
        if conn:
            conn.close()


@contracts_bp.route('/contracts', methods=['POST'])
def create_contract():
    data = request.get_json(silent=True) or {}
    contract_name = data.get('contract_name', '').strip()
    if not contract_name:
        return jsonify({'error': 'contract_name is required'}), 400

    description = data.get('description', '')
    min_sender_balance = data.get('min_sender_balance', 0)
    max_transfer_amount = data.get('max_transfer_amount')
    if max_transfer_amount is None:
        return jsonify({'error': 'max_transfer_amount is required'}), 400

    try:
        min_sender_balance = float(min_sender_balance)
        max_transfer_amount = float(max_transfer_amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'Balance/amount fields must be numeric'}), 400

    if min_sender_balance < 0 or max_transfer_amount <= 0:
        return jsonify({'error': 'min_sender_balance >= 0 and max_transfer_amount > 0 required'}), 400

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contracts (contract_name, description, min_sender_balance, max_transfer_amount) "
            "VALUES (%s, %s, %s, %s)",
            (contract_name, description, min_sender_balance, max_transfer_amount)
        )
        new_id = cursor.lastrowid

        # Insert contract_conditions
        cursor.execute(
            "INSERT INTO contract_conditions (contract_id, condition_type, condition_value, description) "
            "VALUES (%s, %s, %s, %s)",
            (new_id, 'MIN_SENDER_BALANCE', min_sender_balance,
             f'Sender must have at least {min_sender_balance} balance')
        )
        cursor.execute(
            "INSERT INTO contract_conditions (contract_id, condition_type, condition_value, description) "
            "VALUES (%s, %s, %s, %s)",
            (new_id, 'MAX_TRANSFER_AMOUNT', max_transfer_amount,
             f'Transfer amount must not exceed {max_transfer_amount}')
        )
        conn.commit()

        # Fetch the created contract
        cursor.execute(
            "SELECT contract_id, contract_name, description, "
            "CAST(min_sender_balance AS CHAR) as min_sender_balance, "
            "CAST(max_transfer_amount AS CHAR) as max_transfer_amount, "
            "is_active, created_at FROM contracts WHERE contract_id = %s",
            (new_id,)
        )
        columns = [d[0] for d in cursor.description]
        c = _serialize_contract(cursor.fetchone(), columns)

        cursor.execute(
            "SELECT condition_id, condition_type, "
            "CAST(condition_value AS CHAR) as condition_value, description "
            "FROM contract_conditions WHERE contract_id = %s",
            (new_id,)
        )
        cond_cols = [d[0] for d in cursor.description]
        c['conditions'] = [dict(zip(cond_cols, r)) for r in cursor.fetchall()]
        cursor.close()
        return jsonify(c), 201
    except Exception as exc:
        logger.error('create_contract error: %s', exc, exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'error': 'Failed to create contract'}), 500
    finally:
        if conn:
            conn.close()


@contracts_bp.route('/contracts/<int:contract_id>/status', methods=['PATCH'])
def toggle_contract_status(contract_id):
    data = request.get_json(silent=True) or {}
    if 'is_active' not in data:
        return jsonify({'error': 'is_active field is required'}), 400
    is_active = bool(data['is_active'])

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE contracts SET is_active = %s WHERE contract_id = %s",
            (is_active, contract_id)
        )
        if cursor.rowcount == 0:
            cursor.close()
            return jsonify({'error': 'Contract not found'}), 404
        conn.commit()

        cursor.execute(
            "SELECT contract_id, contract_name, description, "
            "CAST(min_sender_balance AS CHAR) as min_sender_balance, "
            "CAST(max_transfer_amount AS CHAR) as max_transfer_amount, "
            "is_active, created_at FROM contracts WHERE contract_id = %s",
            (contract_id,)
        )
        columns = [d[0] for d in cursor.description]
        c = _serialize_contract(cursor.fetchone(), columns)

        cursor.execute(
            "SELECT condition_id, condition_type, "
            "CAST(condition_value AS CHAR) as condition_value, description "
            "FROM contract_conditions WHERE contract_id = %s",
            (contract_id,)
        )
        cond_cols = [d[0] for d in cursor.description]
        c['conditions'] = [dict(zip(cond_cols, r)) for r in cursor.fetchall()]
        cursor.close()
        return jsonify(c)
    except Exception as exc:
        logger.error('toggle_contract_status error: %s', exc, exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'error': 'Failed to update contract status'}), 500
    finally:
        if conn:
            conn.close()
