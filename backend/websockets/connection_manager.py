from fastapi import WebSocket
from typing import Dict, List, Set, Any
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket connection manager for real-time multiplayer poker
    Manages connections, rooms, and message broadcasting
    """
    def __init__(self):
        # Table/Game ID -> List of WebSocket connections
        self.table_connections: Dict[str, List[WebSocket]] = {}
        # Username -> WebSocket connection
        self.user_connections: Dict[str, WebSocket] = {}
        # Username -> Table/Game ID
        self.user_tables: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, table_id: str, username: str):
        """Connect a new WebSocket client to a specific table"""
        await websocket.accept()
        logger.info(f"User {username} connected to table {table_id}")
        
        # Register the connection
        if table_id not in self.table_connections:
            self.table_connections[table_id] = []
        
        self.table_connections[table_id].append(websocket)
        self.user_connections[username] = websocket
        self.user_tables[username] = table_id
        
        # Notify everyone in the table about the new player
        await self.broadcast_to_table(
            table_id,
            {
                "type": "player_joined",
                "username": username
            }
        )
    
    def disconnect(self, websocket: WebSocket, username: str):
        """Disconnect a client and clean up"""
        logger.info(f"Disconnecting user {username}")
        
        # Remove from user connections
        if username in self.user_connections:
            del self.user_connections[username]
        
        # Get the table ID and remove from table connections
        table_id = self.user_tables.get(username)
        if table_id and table_id in self.table_connections:
            if websocket in self.table_connections[table_id]:
                self.table_connections[table_id].remove(websocket)
            
            # Notify others about the disconnect
            asyncio.create_task(self.broadcast_to_table(
                table_id,
                {
                    "type": "player_left",
                    "username": username
                }
            ))
        
        # Remove from user tables
        if username in self.user_tables:
            del self.user_tables[username]
    
    async def broadcast_to_table(self, table_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections in a table"""
        if table_id not in self.table_connections:
            return
        
        # Convert dict to JSON string
        message_json = json.dumps(message)
        
        # Send to all connections in the table
        for connection in self.table_connections[table_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending message to connection: {e}")
    
    async def send_personal_message(self, username: str, message: Dict[str, Any]):
        """Send a message to a specific user"""
        if username not in self.user_connections:
            return
        
        message_json = json.dumps(message)
        
        try:
            await self.user_connections[username].send_text(message_json)
        except Exception as e:
            logger.error(f"Error sending personal message to {username}: {e}")
    
    async def update_game_state(self, table_id: str, game_state: Dict[str, Any]):
        """Update game state for all users in a table, with hidden opponent cards"""
        if table_id not in self.table_connections:
            return
            
        # For each user in the table, send them their own view of the game state
        for username in [user for user, tid in self.user_tables.items() if tid == table_id]:
            # Create a player-specific view (hide opponent cards)
            player_view = self._create_player_view(game_state, username)
            
            await self.send_personal_message(
                username,
                {
                    "type": "game_update",
                    "state": player_view
                }
            )
    
    def _create_player_view(self, game_state: Dict[str, Any], username: str) -> Dict[str, Any]:
        """Create a player-specific view of the game state (hide opponent cards)"""
        # Make a copy of the game state
        player_view = game_state.copy()
        
        # Create a new "hands" dictionary with only the player's own cards
        hands = game_state.get('hands', {}).copy()
        for player, cards in hands.items():
            if player != username:
                # Replace opponent cards with hidden values
                hands[player] = ["??" for _ in cards]
        
        # Update the player view with modified hands
        player_view['hands'] = hands
        
        return player_view


# Create a singleton instance
connection_manager = ConnectionManager()
