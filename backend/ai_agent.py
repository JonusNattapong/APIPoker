import random

def ai_choose_action(game_state: dict, player_name: str) -> dict:
    # Basic AI: random action
    actions = ['fold', 'call', 'raise']
    action = random.choice(actions)
    amount = None
    if action == 'raise':
        amount = game_state['current_bet'] + 10
    return {'action': action, 'amount': amount}
