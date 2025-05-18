import json
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import timedelta
import json

from . import models, schemas, database, auth
from .poker_logic import PokerGame, decide_winner
from .ai_agent import ai_choose_action
from database import engine, SessionLocal, get_db
from auth import get_current_user
from tournaments import tournament_router
from ml_models.poker_model import PokerAIModel
from websockets.handlers import handle_websocket_connection

app = FastAPI(title="APIPoker Backend", description="Backend API for APIPoker platform")

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include tournament router
app.include_router(tournament_router)

# Initialize database
# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize ML model for AI
ai_model = PokerAIModel()

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

# WebSocket endpoint for real-time game updates
@app.websocket("/ws/{game_id}/{username}")
async def websocket_endpoint(
    websocket: WebSocket, 
    game_id: str, 
    username: str,
    db: Session = Depends(get_db)
):
    await handle_websocket_connection(websocket, game_id, username, db)

# AI Action endpoint - use ML model for decision making
@app.get("/ai/action/{game_id}/{ai_name}")
async def ai_action(
    game_id: int, 
    ai_name: str,
    db: Session = Depends(get_db)
):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Parse game state
    import json
    game_state = json.loads(game.state)
    
    # Get AI decision using ML model
    decision = ai_model.predict_action(game_state, ai_name)
    
    return {
        "action": decision["action"],
        "amount": decision["amount"],
        "ai_name": ai_name
    }

# Add leaderboard endpoint
@app.get("/leaderboard", response_model=List[schemas.LeaderboardEntry])
async def get_leaderboard(
    time_period: str = "all",  # all, month, week
    limit: int = 10,
    db: Session = Depends(get_db)
):
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    query = db.query(
        models.User.id,
        models.User.username,
        models.User.tournaments_played,
        models.User.tournaments_won,
        models.User.total_winnings,
        models.User.rank_points
    )
    
    # Apply time period filter if needed
    if time_period == "month":
        # Logic for monthly leaderboard
        month_ago = datetime.now() - timedelta(days=30)
        query = query.filter(models.User.created_at >= month_ago)
    elif time_period == "week":
        # Logic for weekly leaderboard
        week_ago = datetime.now() - timedelta(days=7)
        query = query.filter(models.User.created_at >= week_ago)
    
    # Get results ordered by rank points
    users = query.order_by(desc(models.User.rank_points)).limit(limit).all()
    
    # Format results
    result = []
    for user in users:
        result.append({
            "user_id": user.id,
            "username": user.username,
            "tournaments_played": user.tournaments_played,
            "tournaments_won": user.tournaments_won,
            "total_winnings": float(user.total_winnings),
            "rank_points": user.rank_points
        })
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
