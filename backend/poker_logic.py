import random
from typing import List, Dict, Any

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
    def __repr__(self):
        return f'{self.rank}{self.suit}'
    def __str__(self):
        return f'{self.rank}{self.suit}'

class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)
    def draw(self, n=1):
        return [self.cards.pop() for _ in range(n)]

class PokerGame:
    def __init__(self, players: List[str]):
        self.players = players
        self.hands: Dict[str, List[Card]] = {p: [] for p in players}
        self.deck = Deck()
        self.community: List[Card] = []
        self.pot = 0
        self.current_bet = 0
        self.active_players = set(players)
        self.bets = {p: 0 for p in players}
        self.deal()
    def deal(self):
        for p in self.players:
            self.hands[p] = self.deck.draw(2)
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.active_players = set(self.players)
        self.bets = {p: 0 for p in self.players}
    def flop(self):
        self.community += self.deck.draw(3)
    def turn(self):
        self.community += self.deck.draw(1)
    def river(self):
        self.community += self.deck.draw(1)
    def to_dict(self):
        return {
            'players': self.players,
            'hands': {p: [str(c) for c in self.hands[p]] for p in self.players},
            'community': [str(c) for c in self.community],
            'pot': self.pot,
            'current_bet': self.current_bet,
            'active_players': list(self.active_players),
            'bets': self.bets
        }

# --- Poker Hand Evaluator (simplified) ---
def evaluate_hand(player_hand: List[Card], community: List[Card]) -> int:
    # Dummy: just use the highest card (for MVP)
    all_cards = player_hand + community
    rank_order = {r: i for i, r in enumerate(RANKS)}
    max_rank = max(all_cards, key=lambda c: rank_order[c.rank])
    return rank_order[max_rank.rank]

# --- Winner decision (simplified) ---
def decide_winner(game: PokerGame) -> List[str]:
    best_score = -1
    winners = []
    for p in game.active_players:
        score = evaluate_hand(game.hands[p], game.community)
        if score > best_score:
            best_score = score
            winners = [p]
        elif score == best_score:
            winners.append(p)
    return winners
