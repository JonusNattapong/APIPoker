import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from typing import List, Dict, Any

class PokerAIModel:
    """
    Machine Learning model for poker AI decision making
    Uses Random Forest to predict optimal actions based on game state
    """
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), 'poker_rf_model.joblib')
        self.load_or_create_model()
        
    def load_or_create_model(self):
        """Load existing model or create a new one if not exists"""
        try:
            self.model = joblib.load(self.model_path)
            print("Loaded existing AI model")
        except FileNotFoundError:
            print("Creating new AI model")
            self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            # We'll train with sample data initially
            self._initial_training()
            joblib.dump(self.model, self.model_path)
    
    def _initial_training(self):
        """Train with initial sample data"""
        # Sample features:
        # [pot_size, current_bet, player_chips, hand_strength, community_cards_count, active_players_count]
        X_sample = np.array([
            [100, 10, 900, 0.9, 0, 3],  # Strong hand preflop -> raise
            [100, 10, 900, 0.2, 0, 3],  # Weak hand preflop -> fold
            [200, 20, 800, 0.6, 3, 3],  # Medium hand after flop -> call
            [400, 50, 600, 0.8, 5, 2],  # Strong hand at river -> raise
            [400, 100, 500, 0.4, 5, 2], # Weak hand at river -> fold
        ])
        
        # 0=fold, 1=call, 2=raise
        y_sample = np.array([2, 0, 1, 2, 0])
        
        self.model.fit(X_sample, y_sample)
    
    def evaluate_hand_strength(self, player_hand: List[str], community: List[str]) -> float:
        """
        Evaluate hand strength on scale 0.0-1.0
        More sophisticated version would use actual poker hand evaluation
        """
        # Simplified evaluation for MVP
        # This would be replaced by a more robust evaluation using actual hand rankings
        hand_ranks = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        
        # Extract just the ranks
        player_ranks = [card[:-1] for card in player_hand]
        community_ranks = [card[:-1] for card in community] if community else []
        
        # Convert ranks to values
        player_values = [hand_ranks.get(rank, 0) for rank in player_ranks]
        
        # Basic strength is average of your cards / maximum possible (pair of aces)
        strength = sum(player_values) / 28.0  # 28 = 14+14 (pair of aces)
        
        # Bonus for pairs
        if len(player_ranks) == 2 and player_ranks[0] == player_ranks[1]:
            strength += 0.3
        
        # If we have community cards, add bonus for matching
        if community_ranks:
            for p_rank in player_ranks:
                if p_rank in community_ranks:
                    strength += 0.1
        
        return min(max(strength, 0.0), 1.0)  # Ensure between 0 and 1
    
    def predict_action(self, game_state: Dict[str, Any], player_name: str) -> Dict[str, Any]:
        """Predict best action (fold, call, raise) based on game state"""
        # Extract player's hand
        player_hand = game_state['hands'][player_name]
        community = game_state['community']
        
        # Calculate hand strength
        hand_strength = self.evaluate_hand_strength(player_hand, community)
        
        # Extract features for prediction
        pot = game_state['pot']
        current_bet = game_state['current_bet']
        player_chips = 1000 - game_state['bets'][player_name]  # Assuming starting chips = 1000
        community_cards_count = len(community)
        active_players_count = len(game_state['active_players'])
        
        # Feature vector
        features = np.array([[
            pot, 
            current_bet, 
            player_chips, 
            hand_strength,
            community_cards_count, 
            active_players_count
        ]])
        
        # Predict action (0=fold, 1=call, 2=raise)
        action_code = self.model.predict(features)[0]
        
        # Convert to action dict
        if action_code == 0:
            return {'action': 'fold', 'amount': None}
        elif action_code == 1:
            return {'action': 'call', 'amount': None}
        else:
            # For raise, calculate a reasonable amount
            min_raise = current_bet + 10
            if hand_strength > 0.8:  # Very strong hand
                amount = min(current_bet * 3, player_chips)
            elif hand_strength > 0.6:  # Good hand
                amount = min(current_bet * 2, player_chips)
            else:  # Decent hand
                amount = min_raise
            
            return {'action': 'raise', 'amount': amount}
    
    def update_model(self, game_history: List[Dict[str, Any]]):
        """Update model with new game data (for online learning)"""
        # Extract features and outcomes from game history
        X_new = []
        y_new = []
        
        for game_record in game_history:
            # Extract relevant features and outcome
            # In real implementation, would extract features similar to predict_action
            # and outcomes (whether action led to winning)
            pass
        
        # If we have new data, update the model
        if X_new and y_new:
            X_new = np.array(X_new)
            y_new = np.array(y_new)
            self.model.fit(X_new, y_new)
            # Save updated model
            joblib.dump(self.model, self.model_path)
