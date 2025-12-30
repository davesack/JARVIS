from utils.tokens.storage import get_db
from datetime import date, timedelta

def get_daily_streak(user_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT DISTINCT date FROM chore_log WHERE user_id = ? ORDER BY date DESC",
            (user_id,)
        ).fetchall()

    streak = 0
    today = date.today()

    for i, row in enumerate(rows):
        if row[0] == str(today - timedelta(days=i)):
            streak += 1
        else:
            break

    return streak
