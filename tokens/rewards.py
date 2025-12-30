from utils.tokens.storage import get_db

def list_rewards():
    with get_db() as db:
        return db.execute(
            "SELECT name, cost FROM rewards WHERE active = 1"
        ).fetchall()
