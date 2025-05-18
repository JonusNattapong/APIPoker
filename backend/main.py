import json
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import timedelta
import json

from . import models, schemas, database, auth
from .poker_logic import PokerGame, decide_winner
from .ai_agent import ai_choose_action

app = FastAPI(title="APIPoker - Production-ready Poker API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, limit this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
models.Base.metadata.create_all(bind=database.engine)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth Routes ---
@app.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = auth.get_user(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id, "username": user.username}

# --- User Routes ---
@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# --- Table Routes ---
@app.post("/tables", response_model=schemas.TableOut)
def create_table(table: schemas.TableCreate, db: Session = Depends(get_db), 
                current_user: models.User = Depends(auth.get_current_user)):
    db_table = models.Table(name=table.name, owner_id=current_user.id)
    db.add(db_table)
    db.commit()
    db.refresh(db_table)
    return db_table

@app.get("/tables", response_model=List[schemas.TableOut])
def list_tables(db: Session = Depends(get_db)):
    tables = db.query(models.Table).all()
    return tables

# --- Game Routes ---
@app.post("/games", response_model=schemas.GameOut)
def create_game(game: schemas.GameCreate, db: Session = Depends(get_db), 
               current_user: models.User = Depends(auth.get_current_user)):
    # Check if table exists
    table = db.query(models.Table).filter(models.Table.id == game.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Create a poker game with the current user and AI
    poker_game = PokerGame(players=[current_user.username, "ai_player"])
    
    # Save the game state
    game_state = json.dumps(poker_game.to_dict())
    db_game = models.Game(table_id=game.table_id, owner_id=current_user.id, state=game_state)
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game

@app.get("/games/{game_id}", response_model=schemas.GameOut)
def get_game(game_id: int, db: Session = Depends(get_db)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

# --- Poker Game Actions ---
@app.post("/games/{game_id}/action")
def player_action(game_id: int, action: str, amount: Optional[int] = None, 
                 db: Session = Depends(get_db),
                 current_user: models.User = Depends(auth.get_current_user)):
    # Get the game
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Parse the current game state
    game_state = json.loads(game.state)
    poker_game = PokerGame(game_state['players'])
    poker_game.hands = {p: [poker_game.Card(c[-1], c[:-1]) for c in game_state['hands'][p]] for p in game_state['players']}
    poker_game.community = [poker_game.Card(c[-1], c[:-1]) for c in game_state['community']]
    poker_game.pot = game_state['pot']
    poker_game.current_bet = game_state['current_bet']
    poker_game.active_players = set(game_state['active_players'])
    poker_game.bets = game_state['bets']
    
    # Process player action
    if current_user.username not in poker_game.active_players:
        raise HTTPException(status_code=400, detail="Player not active")
        
    if action == 'fold':
        poker_game.active_players.remove(current_user.username)
    elif action == 'call':
        bet = poker_game.current_bet - poker_game.bets[current_user.username]
        poker_game.bets[current_user.username] += bet
        poker_game.pot += bet
    elif action == 'raise':
        if amount is None or amount <= poker_game.current_bet:
            raise HTTPException(status_code=400, detail="Invalid raise amount")
        bet = amount - poker_game.bets[current_user.username]
        poker_game.current_bet = amount
        poker_game.bets[current_user.username] += bet
        poker_game.pot += bet
    else:
        raise HTTPException(status_code=400, detail="Unknown action")
    
    # AI's turn
    if "ai_player" in poker_game.active_players:
        ai_decision = ai_choose_action(poker_game.to_dict(), "ai_player")
        ai_action = ai_decision['action']
        
        if ai_action == 'fold':
            poker_game.active_players.remove("ai_player")
        elif ai_action == 'call':
            bet = poker_game.current_bet - poker_game.bets["ai_player"]
            poker_game.bets["ai_player"] += bet
            poker_game.pot += bet
        elif ai_action == 'raise':
            amount = ai_decision['amount']
            bet = amount - poker_game.bets["ai_player"]
            poker_game.current_bet = amount
            poker_game.bets["ai_player"] += bet
            poker_game.pot += bet
    
    # Update game state in DB
    game.state = json.dumps(poker_game.to_dict())
    db.commit()
    
    return {"message": "Action processed", "state": poker_game.to_dict()}

@app.post("/games/{game_id}/flop")
def deal_flop(game_id: int, db: Session = Depends(get_db),
             current_user: models.User = Depends(auth.get_current_user)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Parse game state
    game_state = json.loads(game.state)
    poker_game = PokerGame(game_state['players'])
    poker_game.hands = {p: [poker_game.Card(c[-1], c[:-1]) for c in game_state['hands'][p]] for p in game_state['players']}
    poker_game.community = [poker_game.Card(c[-1], c[:-1]) for c in game_state['community']]
    poker_game.pot = game_state['pot']
    poker_game.current_bet = game_state['current_bet']
    poker_game.active_players = set(game_state['active_players'])
    poker_game.bets = game_state['bets']
    
    # Deal flop
    poker_game.flop()
    
    # Update game state
    game.state = json.dumps(poker_game.to_dict())
    db.commit()
    
    return {"message": "Flop dealt", "state": poker_game.to_dict()}

@app.post("/games/{game_id}/turn")
def deal_turn(game_id: int, db: Session = Depends(get_db),
             current_user: models.User = Depends(auth.get_current_user)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Parse game state
    game_state = json.loads(game.state)
    poker_game = PokerGame(game_state['players'])
    poker_game.hands = {p: [poker_game.Card(c[-1], c[:-1]) for c in game_state['hands'][p]] for p in game_state['players']}
    poker_game.community = [poker_game.Card(c[-1], c[:-1]) for c in game_state['community']]
    poker_game.pot = game_state['pot']
    poker_game.current_bet = game_state['current_bet']
    poker_game.active_players = set(game_state['active_players'])
    poker_game.bets = game_state['bets']
    
    # Deal turn
    poker_game.turn()
    
    # Update game state
    game.state = json.dumps(poker_game.to_dict())
    db.commit()
    
    return {"message": "Turn dealt", "state": poker_game.to_dict()}

@app.post("/games/{game_id}/river")
def deal_river(game_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(auth.get_current_user)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Parse game state
    game_state = json.loads(game.state)
    poker_game = PokerGame(game_state['players'])
    poker_game.hands = {p: [poker_game.Card(c[-1], c[:-1]) for c in game_state['hands'][p]] for p in game_state['players']}
    poker_game.community = [poker_game.Card(c[-1], c[:-1]) for c in game_state['community']]
    poker_game.pot = game_state['pot']
    poker_game.current_bet = game_state['current_bet']
    poker_game.active_players = set(game_state['active_players'])
    poker_game.bets = game_state['bets']
    
    # Deal river
    poker_game.river()
    
    # Update game state
    game.state = json.dumps(poker_game.to_dict())
    db.commit()
    
    return {"message": "River dealt", "state": poker_game.to_dict()}

@app.post("/games/{game_id}/showdown")
def showdown(game_id: int, db: Session = Depends(get_db),
            current_user: models.User = Depends(auth.get_current_user)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Parse game state
    game_state = json.loads(game.state)
    poker_game = PokerGame(game_state['players'])
    poker_game.hands = {p: [poker_game.Card(c[-1], c[:-1]) for c in game_state['hands'][p]] for p in game_state['players']}
    poker_game.community = [poker_game.Card(c[-1], c[:-1]) for c in game_state['community']]
    poker_game.pot = game_state['pot']
    poker_game.current_bet = game_state['current_bet']
    poker_game.active_players = set(game_state['active_players'])
    poker_game.bets = game_state['bets']
    
    # Find winners
    winners = decide_winner(poker_game)
    
    # Distribute pot
    pot_per_winner = poker_game.pot / len(winners)
    
    # Credit winners
    for winner in winners:
        if winner == current_user.username:
            user = db.query(models.User).filter(models.User.id == current_user.id).first()
            user.credits += pot_per_winner
            db.commit()
    
    return {"message": "Showdown completed", "winners": winners, "pot_per_winner": pot_per_winner}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
