from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from poker_game import PokerGame

app = FastAPI()

# Store games in memory (for demo)
games: Dict[str, PokerGame] = {}

class CreateGameRequest(BaseModel):
    game_id: str
    players: List[str]

class ActionRequest(BaseModel):
    game_id: str
    player: str
    action: str  # 'fold', 'call', 'raise'
    amount: Optional[int] = None

class GameIdRequest(BaseModel):
    game_id: str

@app.post('/create_game')
def create_game(req: CreateGameRequest):
    if req.game_id in games:
        raise HTTPException(status_code=400, detail='Game already exists')
    games[req.game_id] = PokerGame(req.players)
    return {'msg': 'Game created', 'game_id': req.game_id}

@app.get('/game_state/{game_id}')
def game_state(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail='Game not found')
    return games[game_id].to_dict()

import random

@app.post('/action')
def player_action(req: ActionRequest):
    if req.game_id not in games:
        raise HTTPException(status_code=404, detail='Game not found')
    game = games[req.game_id]
    if req.player not in game.active_players:
        raise HTTPException(status_code=400, detail='Player not active')
    # Simple action logic for demo
    if req.action == 'fold':
        game.active_players.remove(req.player)
    elif req.action == 'call':
        bet = game.current_bet - game.bets[req.player]
        game.bets[req.player] += bet
        game.pot += bet
    elif req.action == 'raise':
        if req.amount is None or req.amount <= game.current_bet:
            raise HTTPException(status_code=400, detail='Invalid raise amount')
        bet = req.amount - game.bets[req.player]
        game.current_bet = req.amount
        game.bets[req.player] += bet
        game.pot += bet
    else:
        raise HTTPException(status_code=400, detail='Unknown action')

    # --- AI agent logic ---
    # สมมติชื่อผู้เล่นมนุษย์คือ 'user' ที่เหลือเป็น AI
    ai_players = [p for p in game.active_players if not p.lower().startswith('user')]
    for ai in ai_players:
        # AI จะสุ่ม action (call, raise, fold)
        possible_actions = ['call', 'raise', 'fold']
        action = random.choice(possible_actions)
        if action == 'fold':
            game.active_players.remove(ai)
        elif action == 'call':
            bet = game.current_bet - game.bets[ai]
            game.bets[ai] += bet
            game.pot += bet
        elif action == 'raise':
            # AI raise เป็น current_bet + 10
            amount = game.current_bet + 10
            bet = amount - game.bets[ai]
            game.current_bet = amount
            game.bets[ai] += bet
            game.pot += bet
    # --- END AI agent logic ---

    return {'msg': 'Action processed (with AI moves)', 'state': game.to_dict()}

@app.post('/flop')
def flop(req: GameIdRequest):
    if req.game_id not in games:
        raise HTTPException(status_code=404, detail='Game not found')
    games[req.game_id].flop()
    return {'msg': 'Flop dealt', 'state': games[req.game_id].to_dict()}

@app.post('/turn')
def turn(req: GameIdRequest):
    if req.game_id not in games:
        raise HTTPException(status_code=404, detail='Game not found')
    games[req.game_id].turn()
    return {'msg': 'Turn dealt', 'state': games[req.game_id].to_dict()}

@app.post('/river')
def river(req: GameIdRequest):
    if req.game_id not in games:
        raise HTTPException(status_code=404, detail='Game not found')
    games[req.game_id].river()
    return {'msg': 'River dealt', 'state': games[req.game_id].to_dict()}
