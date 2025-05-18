from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Tournament Schemas
class TournamentBase(BaseModel):
    name: str
    description: Optional[str] = None
    buy_in: float = 100.0
    max_players: int = 8
    blind_increase_minutes: int = 15
    initial_stack: int = 1000
    start_time: datetime

class TournamentCreate(TournamentBase):
    pass

class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    buy_in: Optional[float] = None
    max_players: Optional[int] = None
    blind_increase_minutes: Optional[int] = None
    initial_stack: Optional[int] = None
    start_time: Optional[datetime] = None
    status: Optional[str] = None

class TournamentParticipantBase(BaseModel):
    user_id: int
    tournament_id: int

class TournamentParticipantCreate(TournamentParticipantBase):
    pass

class TournamentParticipantOut(TournamentParticipantBase):
    id: int
    status: str
    final_position: Optional[int] = None
    chips: int
    points_earned: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class UserBasicInfo(BaseModel):
    id: int
    username: str

class TournamentParticipantWithUser(TournamentParticipantOut):
    user: UserBasicInfo
    
    class Config:
        orm_mode = True

class TournamentOut(TournamentBase):
    id: int
    prize_pool: float
    status: str
    end_time: Optional[datetime] = None
    created_at: datetime
    created_by_id: int
    participants_count: int
    
    class Config:
        orm_mode = True

class TournamentDetailOut(TournamentOut):
    participants: List[TournamentParticipantWithUser]
    
    class Config:
        orm_mode = True

# Leaderboard Schemas
class LeaderboardEntry(BaseModel):
    user_id: int
    username: str
    tournaments_played: int
    tournaments_won: int
    total_winnings: float
    rank_points: int
    highest_position: int

class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
    total_players: int
