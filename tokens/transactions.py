from utils.tokens.storage import get_db
from datetime import datetime

def add_transaction(user_id, amount, reason, issued_by):
    with get_db() as db:
        db.execute(
            """INSERT INTO transactions
               (user_id, amount, reason, issued_by, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, amount, reason, issued_by, datetime.utcnow())
        )

def get_balance(user_id):
    with get_db() as db:
        cur = db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = ?",
            (user_id,)
        )
        return cur.fetchone()[0]
