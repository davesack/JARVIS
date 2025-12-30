from utils.tokens.transactions import add_transaction, get_balance

def redeem(user_id, reward_cost, reward_name):
    balance = get_balance(user_id)
    if balance < reward_cost:
        return False

    add_transaction(
        user_id,
        -reward_cost,
        f"Redeemed: {reward_name}",
        issued_by=0
    )
    return True
