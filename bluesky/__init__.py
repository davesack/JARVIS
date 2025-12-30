from datetime import datetime


def log(message: str):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[BLUESKY {ts}] {message}")


__all__ = ["log"]
