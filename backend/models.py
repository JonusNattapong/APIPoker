from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    credits = Column(Float, default=1000)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    games = relationship('Game', back_populates='owner')
    
    # Leaderboard stats
    tournaments_played = Column(Integer, default=0)
    tournaments_won = Column(Integer, default=0)
    total_winnings = Column(Float, default=0)
    rank_points = Column(Integer, default=0)
    
    # Tournament relationships
    created_tournaments = relationship('Tournament', back_populates='created_by', foreign_keys='Tournament.created_by_id')

class Table(Base):
    __tablename__ = 'tables'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    games = relationship('Game', back_populates='table')

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey('tables.id'))
    owner_id = Column(Integer, ForeignKey('users.id'))
    state = Column(String)  # JSON string of game state
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    table = relationship('Table', back_populates='games')
    owner = relationship('User', back_populates='games')
    
    # Tournament relationship
    tournament_table_id = Column(Integer, ForeignKey('tournament_tables.id'), nullable=True)
    is_tournament_game = Column(Boolean, default=False)
