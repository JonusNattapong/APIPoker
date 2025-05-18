from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base

class TournamentStatus(str, enum.Enum):
    PENDING = "pending"
    REGISTERING = "registering"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ParticipantStatus(str, enum.Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    ELIMINATED = "eliminated"
    WINNER = "winner"

class Tournament(Base):
    """Tournament model for organizing poker tournaments"""
    __tablename__ = 'tournaments'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    buy_in = Column(Float, default=100.0)
    prize_pool = Column(Float, default=0.0)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default=TournamentStatus.PENDING)
    max_players = Column(Integer, default=8)
    blind_increase_minutes = Column(Integer, default=15)
    initial_stack = Column(Integer, default=1000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    created_by = relationship("User", back_populates="created_tournaments")
    participants = relationship("TournamentParticipant", back_populates="tournament")
    rounds = relationship("TournamentRound", back_populates="tournament")

class TournamentParticipant(Base):
    """Model for players participating in tournaments"""
    __tablename__ = 'tournament_participants'
    
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String, default=ParticipantStatus.REGISTERED)
    final_position = Column(Integer, nullable=True)
    chips = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tournament = relationship("Tournament", back_populates="participants")
    user = relationship("User")

class TournamentRound(Base):
    """Model for tournament rounds/stages"""
    __tablename__ = 'tournament_rounds'
    
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    round_number = Column(Integer)
    small_blind = Column(Integer)
    big_blind = Column(Integer)
    status = Column(String, default="pending")  # pending, active, completed
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tournament = relationship("Tournament", back_populates="rounds")
    tables = relationship("TournamentTable", back_populates="round")

class TournamentTable(Base):
    """Model for tables within a tournament round"""
    __tablename__ = 'tournament_tables'
    
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    round_id = Column(Integer, ForeignKey('tournament_rounds.id'))
    table_number = Column(Integer)
    status = Column(String, default="pending")  # pending, active, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    round = relationship("TournamentRound", back_populates="tables")
    games = relationship("Game")
