from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from .. import models
from ..auth import get_current_user
from . import schemas
from .models import Tournament, TournamentParticipant, TournamentStatus, ParticipantStatus

router = APIRouter(
    prefix="/tournaments",
    tags=["tournaments"],
)

@router.post("/", response_model=schemas.TournamentOut)
def create_tournament(
    tournament: schemas.TournamentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new tournament"""
    if tournament.start_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament start time must be in the future"
        )
    
    new_tournament = Tournament(
        name=tournament.name,
        description=tournament.description,
        buy_in=tournament.buy_in,
        max_players=tournament.max_players,
        blind_increase_minutes=tournament.blind_increase_minutes,
        initial_stack=tournament.initial_stack,
        start_time=tournament.start_time,
        status=TournamentStatus.REGISTERING,
        created_by_id=current_user.id
    )
    
    db.add(new_tournament)
    db.commit()
    db.refresh(new_tournament)
    
    # Add creator as first participant
    participant = TournamentParticipant(
        tournament_id=new_tournament.id,
        user_id=current_user.id,
        status=ParticipantStatus.REGISTERED,
        chips=new_tournament.initial_stack
    )
    
    # Deduct buy-in from user's credits
    current_user.credits -= tournament.buy_in
    
    # Add to prize pool
    new_tournament.prize_pool += tournament.buy_in
    
    db.add(participant)
    db.commit()
    db.refresh(new_tournament)
    
    return new_tournament

@router.get("/", response_model=List[schemas.TournamentOut])
def get_tournaments(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get a list of tournaments with filtering options"""
    query = db.query(Tournament)
    
    if status:
        query = query.filter(Tournament.status == status)
    
    tournaments = query.order_by(desc(Tournament.created_at)).offset(skip).limit(limit).all()
    
    # Add participants count to each tournament
    for tournament in tournaments:
        tournament.participants_count = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament.id
        ).count()
    
    return tournaments

@router.get("/{tournament_id}", response_model=schemas.TournamentDetailOut)
def get_tournament(
    tournament_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific tournament including participants"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )
    
    # Count participants
    tournament.participants_count = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id
    ).count()
    
    return tournament

@router.post("/{tournament_id}/register", response_model=schemas.TournamentParticipantOut)
def register_for_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Register current user for a tournament"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )
    
    # Check if tournament is open for registration
    if tournament.status != TournamentStatus.REGISTERING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament is not open for registration (status: {tournament.status})"
        )
    
    # Check if tournament is full
    participants_count = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id
    ).count()
    
    if participants_count >= tournament.max_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is full"
        )
    
    # Check if user is already registered
    existing = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id,
        TournamentParticipant.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already registered for this tournament"
        )
    
    # Check if user has enough credits
    if current_user.credits < tournament.buy_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough credits. Buy-in is {tournament.buy_in} but you have {current_user.credits}"
        )
    
    # Register the user
    participant = TournamentParticipant(
        tournament_id=tournament.id,
        user_id=current_user.id,
        status=ParticipantStatus.REGISTERED,
        chips=tournament.initial_stack
    )
    
    # Deduct buy-in from user credits
    current_user.credits -= tournament.buy_in
    
    # Add to prize pool
    tournament.prize_pool += tournament.buy_in
    
    db.add(participant)
    db.commit()
    db.refresh(participant)
    
    return participant

@router.post("/{tournament_id}/start", response_model=schemas.TournamentOut)
def start_tournament(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Start a tournament (only for tournament creator)"""
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found"
        )
    
    # Check if current user is the creator
    if tournament.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tournament creator can start the tournament"
        )
    
    # Check if tournament can be started
    if tournament.status != TournamentStatus.REGISTERING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tournament cannot be started (status: {tournament.status})"
        )
    
    # Get registered participants
    participants_count = db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id
    ).count()
    
    if participants_count < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 players are required to start a tournament"
        )
    
    # Update tournament status
    tournament.status = TournamentStatus.ACTIVE
    
    # Update all participants to ACTIVE
    db.query(TournamentParticipant).filter(
        TournamentParticipant.tournament_id == tournament.id
    ).update({TournamentParticipant.status: ParticipantStatus.ACTIVE})
    
    # Create first round with initial blinds
    from .models import TournamentRound
    first_round = TournamentRound(
        tournament_id=tournament.id,
        round_number=1,
        small_blind=5,
        big_blind=10,
        status="active",
        start_time=datetime.now()
    )
    
    db.add(first_round)
    db.commit()
    db.refresh(tournament)
    
    # Calculate participants count for response
    tournament.participants_count = participants_count
    
    return tournament

@router.get("/leaderboard", response_model=schemas.LeaderboardResponse)
def get_leaderboard(
    timeframe: str = "all",  # all, month, week
    db: Session = Depends(get_db)
):
    """Get poker leaderboard based on tournament performance"""
    # Build query with filters based on timeframe
    base_query = db.query(
        models.User.id,
        models.User.username,
        func.count(TournamentParticipant.id).label("tournaments_played"),
        func.sum(
            func.case(
                [(TournamentParticipant.final_position == 1, 1)],
                else_=0
            )
        ).label("tournaments_won"),
        func.sum(TournamentParticipant.points_earned).label("rank_points"),
        func.min(
            func.case(
                [(TournamentParticipant.final_position > 0, TournamentParticipant.final_position)],
                else_=999
            )
        ).label("highest_position"),
    ).join(
        TournamentParticipant,
        models.User.id == TournamentParticipant.user_id
    ).group_by(
        models.User.id,
        models.User.username
    )
    
    # Apply time filters
    if timeframe == "month":
        month_ago = datetime.now() - timedelta(days=30)
        base_query = base_query.filter(TournamentParticipant.created_at >= month_ago)
    elif timeframe == "week":
        week_ago = datetime.now() - timedelta(days=7)
        base_query = base_query.filter(TournamentParticipant.created_at >= week_ago)
    
    # Get results ordered by rank points
    leaderboard_entries = base_query.order_by(desc("rank_points")).all()
    
    # Convert to response format with total_winnings calculation
    result = []
    for entry in leaderboard_entries:
        # Get sum of winnings from tournaments
        winnings = db.query(func.sum(Tournament.prize_pool)).join(
            TournamentParticipant,
            Tournament.id == TournamentParticipant.tournament_id
        ).filter(
            TournamentParticipant.user_id == entry.id,
            TournamentParticipant.final_position == 1
        ).scalar() or 0.0
        
        result.append({
            "user_id": entry.id,
            "username": entry.username,
            "tournaments_played": entry.tournaments_played,
            "tournaments_won": entry.tournaments_won,
            "total_winnings": float(winnings),
            "rank_points": entry.rank_points or 0,
            "highest_position": entry.highest_position if entry.highest_position != 999 else None
        })
    
    # Calculate total players
    total_players = len(result)
    
    return {
        "leaderboard": result,
        "total_players": total_players
    }
