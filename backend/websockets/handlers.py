from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import logging
from typing import Dict, Any
import asyncio

from .connection_manager import connection_manager
from .. import models, database
from ..poker_logic import PokerGame
from ..ml_models.poker_model import PokerAIModel

# Set up logging
logger = logging.getLogger(__name__)

# Initialize ML model for AI decisions
ai_model = PokerAIModel()

async def handle_websocket_connection(
    websocket: WebSocket, 
    game_id: str, 
    username: str,
    db: Session = Depends(database.SessionLocal)
):
    """Handle a new WebSocket connection for a game"""
    try:
        # Accept connection and register in connection manager
        await connection_manager.connect(websocket, game_id, username)
        
        # Get initial game state and send to the new player
        game = db.query(models.Game).filter(models.Game.id == int(game_id)).first()
        if game:
            game_state = json.loads(game.state)
            await connection_manager.send_personal_message(
                username, 
                {
                    "type": "initial_state",
                    "state": game_state
                }
            )
        
        # Main WebSocket message handling loop
        while True:
            # Wait for messages from the client
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            
            # Process different message types
            message_type = message.get("type", "")
            
            if message_type == "player_action":
                # Handle player actions (fold, call, raise)
                await handle_player_action(db, game_id, username, message)
            
            elif message_type == "chat":
                # Handle chat messages
                await handle_chat_message(game_id, username, message)
            
            elif message_type == "game_control":
                # Handle game control messages (flop, turn, river, etc.)
                await handle_game_control(db, game_id, username, message)
                
    except WebSocketDisconnect:
        # Handle disconnect
        connection_manager.disconnect(websocket, username)
        logger.info(f"Client {username} disconnected from game {game_id}")
        
    except Exception as e:
        # Log any other errors
        logger.error(f"Error in WebSocket handler: {str(e)}")
        connection_manager.disconnect(websocket, username)

async def handle_player_action(
    db: Session, 
    game_id: str, 
    username: str, 
    message: Dict[str, Any]
):
    """Handle a player action (fold, call, raise)"""
    action = message.get("action")
    amount = message.get("amount")
    logger.info(f"Player {username} action: {action} amount: {amount}")
    
    # Get the game from the database
    game = db.query(models.Game).filter(models.Game.id == int(game_id)).first()
    if not game:
        logger.error(f"Game {game_id} not found")
        return
    
    # Parse the current game state
    game_state = json.loads(game.state)
    poker_game = create_poker_game_from_state(game_state)
    
    # Verify player is active
    if username not in poker_game.active_players:
        logger.error(f"Player {username} is not active in the game")
        return
    
    # Process the action
    if action == 'fold':
        poker_game.active_players.remove(username)
    elif action == 'call':
        bet = poker_game.current_bet - poker_game.bets[username]
        poker_game.bets[username] += bet
        poker_game.pot += bet
    elif action == 'raise':
        if amount is None or amount <= poker_game.current_bet:
            logger.error(f"Invalid raise amount: {amount}")
            return
        bet = amount - poker_game.bets[username]
        poker_game.current_bet = amount
        poker_game.bets[username] += bet
        poker_game.pot += bet
    else:
        logger.error(f"Unknown action: {action}")
        return
    
    # AI's turn - for each AI player, make a move
    for ai_player in [p for p in poker_game.active_players if p.startswith('ai')]:
        ai_decision = ai_model.predict_action(poker_game.to_dict(), ai_player)
        ai_action = ai_decision['action']
        ai_amount = ai_decision['amount']
        
        # Process AI action
        if ai_action == 'fold':
            poker_game.active_players.remove(ai_player)
        elif ai_action == 'call':
            bet = poker_game.current_bet - poker_game.bets[ai_player]
            poker_game.bets[ai_player] += bet
            poker_game.pot += bet
        elif ai_action == 'raise' and ai_amount is not None:
            bet = ai_amount - poker_game.bets[ai_player]
            poker_game.current_bet = ai_amount
            poker_game.bets[ai_player] += bet
            poker_game.pot += bet
    
    # Update game state in database
    game.state = json.dumps(poker_game.to_dict())
    db.commit()
    
    # Broadcast the updated game state to all players
    await connection_manager.update_game_state(game_id, poker_game.to_dict())
    
    # Also broadcast the last action to everyone
    await connection_manager.broadcast_to_table(
        game_id,
        {
            "type": "player_action_update",
            "player": username,
            "action": action,
            "amount": amount
        }
    )
    
    # Check for game end conditions
    if len(poker_game.active_players) <= 1 or len(poker_game.community) == 5:
        await check_game_end(db, game_id, poker_game)

async def handle_chat_message(game_id: str, username: str, message: Dict[str, Any]):
    """Handle a chat message"""
    chat_text = message.get("text", "")
    if not chat_text:
        return
        
    # Broadcast chat message to everyone in the table
    await connection_manager.broadcast_to_table(
        game_id,
        {
            "type": "chat_message",
            "username": username,
            "message": chat_text,
            "timestamp": message.get("timestamp", "")
        }
    )

async def handle_game_control(
    db: Session, 
    game_id: str, 
    username: str, 
    message: Dict[str, Any]
):
    """Handle game control messages (flop, turn, river)"""
    command = message.get("command", "")
    logger.info(f"Game control: {command} by {username} in game {game_id}")
    
    # Get the game from the database
    game = db.query(models.Game).filter(models.Game.id == int(game_id)).first()
    if not game:
        logger.error(f"Game {game_id} not found")
        return
    
    # Parse the game state
    game_state = json.loads(game.state)
    poker_game = create_poker_game_from_state(game_state)
    
    # Process the command
    if command == "flop" and len(poker_game.community) == 0:
        poker_game.flop()
    elif command == "turn" and len(poker_game.community) == 3:
        poker_game.turn()
    elif command == "river" and len(poker_game.community) == 4:
        poker_game.river()
    elif command == "showdown":
        # Will be handled by check_game_end
        pass
    else:
        logger.error(f"Invalid game control command: {command}")
        return
    
    # Update game state in database
    game.state = json.dumps(poker_game.to_dict())
    db.commit()
    
    # Broadcast the updated game state
    await connection_manager.update_game_state(game_id, poker_game.to_dict())
    
    # Also broadcast the game stage update
    await connection_manager.broadcast_to_table(
        game_id,
        {
            "type": "game_stage_update",
            "stage": command,
            "community_cards": [str(c) for c in poker_game.community]
        }
    )
    
    # Check for game end if showdown or all but one player has folded
    if command == "showdown" or len(poker_game.active_players) <= 1:
        await check_game_end(db, game_id, poker_game)

async def check_game_end(db: Session, game_id: str, poker_game: PokerGame):
    """Check if the game has ended and determine the winner"""
    from ..poker_logic import decide_winner
    
    # If only one player is active, they win automatically
    if len(poker_game.active_players) == 1:
        winner = list(poker_game.active_players)[0]
        winners = [winner]
    else:
        # Otherwise determine winner based on hands
        winners = decide_winner(poker_game)
    
    # Split the pot among winners
    pot_per_winner = poker_game.pot / len(winners)
    
    # Update user credits in database
    for winner in winners:
        # Find the user by username
        user = db.query(models.User).filter(models.User.username == winner).first()
        if user:
            user.credits += pot_per_winner
            db.commit()
    
    # Broadcast the game result
    await connection_manager.broadcast_to_table(
        game_id,
        {
            "type": "game_end",
            "winners": winners,
            "pot_per_winner": pot_per_winner,
            "final_state": poker_game.to_dict()
        }
    )

def create_poker_game_from_state(game_state: Dict[str, Any]) -> PokerGame:
    """Create a PokerGame instance from a JSON game state"""
    from ..poker_logic import Card, PokerGame
    
    # Create the poker game
    poker_game = PokerGame(game_state['players'])
    
    # Restore the game state
    poker_game.hands = {p: [Card(c[-1], c[:-1]) for c in game_state['hands'][p]] 
                        for p in game_state['players']}
    poker_game.community = [Card(c[-1], c[:-1]) for c in game_state['community']]
    poker_game.pot = game_state['pot']
    poker_game.current_bet = game_state['current_bet']
    poker_game.active_players = set(game_state['active_players'])
    poker_game.bets = game_state['bets']
    
    return poker_game
