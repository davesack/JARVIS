from utils.tokens.storage import get_db

def list_chores():
    with get_db() as db:
        return db.execute("SELECT name, value FROM chores WHERE active = 1").fetchall()

def log_completion(user_id, chore_name):
    with get_db() as db:
        db.execute(
            "INSERT INTO chore_log (user_id, chore, date) VALUES (?, ?, DATE('now'))",
            (user_id, chore_name)
        )
