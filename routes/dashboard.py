import logging
from decimal import Decimal
from flask import Blueprint, jsonify
from database import get_connection

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api')


def _serialize(val):
    if isinstance(val, Decimal):
        return str(val)
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return val


@dashboard_bp.route('/dashboard')
def dashboard():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Total accounts
        cursor.execute("SELECT COUNT(*) FROM accounts")
        (total_accounts,) = cursor.fetchone()

        # Transaction stats
        cursor.execute(
            """SELECT COUNT(*),
                      SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN status='REJECTED' THEN 1 ELSE 0 END),
                      COALESCE(SUM(CASE WHEN status='SUCCESS' THEN amount ELSE 0 END), 0)
               FROM transactions"""
        )
        row = cursor.fetchone()
        total_transactions = int(row[0]) if row[0] else 0
        successful_transactions = int(row[1]) if row[1] else 0
        rejected_transactions = int(row[2]) if row[2] else 0
        total_volume = str(row[3]) if row[3] is not None else '0.00'

        # Account list
        cursor.execute(
            "SELECT account_id, account_name, CAST(balance AS CHAR) as balance, created_at "
            "FROM accounts ORDER BY account_id"
        )
        columns = [d[0] for d in cursor.description]
        accounts = []
        for r in cursor.fetchall():
            acc = dict(zip(columns, r))
            acc['created_at'] = acc['created_at'].isoformat() if acc['created_at'] else None
            accounts.append(acc)

        cursor.close()
        return jsonify({
            'total_accounts': total_accounts,
            'total_transactions': total_transactions,
            'successful_transactions': successful_transactions,
            'rejected_transactions': rejected_transactions,
            'total_volume': total_volume,
            'accounts': accounts,
        })
    except Exception as exc:
        logger.error('Dashboard error: %s', exc, exc_info=True)
        return jsonify({'error': 'Failed to load dashboard data'}), 500
    finally:
        if conn:
            conn.close()
