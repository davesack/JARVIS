from dataclasses import dataclass
from datetime import datetime

@dataclass
class Transaction:
    user_id: int
    amount: int
    reason: str
    issued_by: int
    timestamp: datetime
