import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

interface Player {
  username: string;
  cards: string[];
  bet: number;
  isActive: boolean;
}

interface GameState {
  players: string[];
  hands: Record<string, string[]>;
  community: string[];
  pot: number;
  current_bet: number;
  active_players: string[];
  bets: Record<string, number>;
}

const PokerTable: React.FC = () => {
  const { tableId } = useParams<{ tableId: string }>();
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [raiseAmount, setRaiseAmount] = useState(10);
  const [gameStage, setGameStage] = useState<'preflop' | 'flop' | 'turn' | 'river' | 'showdown'>('preflop');
  const { username } = useAuth();
  const navigate = useNavigate();

  // Fetch game state on component mount and when gameStage changes
  useEffect(() => {
    fetchGameState();
  }, [tableId, gameStage]);

  const fetchGameState = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get(`http://localhost:8000/games/${tableId}`);
      const state = JSON.parse(response.data.state);
      setGameState(state);
      setError('');
    } catch (err: any) {
      setError('Failed to fetch game state. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (action: 'fold' | 'call' | 'raise') => {
    try {
      const params: any = { action };
      if (action === 'raise') {
        params.amount = raiseAmount;
      }

      await axios.post(`http://localhost:8000/games/${tableId}/action`, params);
      fetchGameState();
    } catch (err: any) {
      setError('Failed to perform action. Please try again.');
      console.error(err);
    }
  };

  const handleDealNext = async () => {
    try {
      let endpoint = '';
      switch (gameStage) {
        case 'preflop':
          endpoint = 'flop';
          setGameStage('flop');
          break;
        case 'flop':
          endpoint = 'turn';
          setGameStage('turn');
          break;
        case 'turn':
          endpoint = 'river';
          setGameStage('river');
          break;
        case 'river':
          endpoint = 'showdown';
          setGameStage('showdown');
          break;
        default:
          // Reset game
          navigate('/lobby');
          return;
      }

      await axios.post(`http://localhost:8000/games/${tableId}/${endpoint}`);
      fetchGameState();
    } catch (err: any) {
      setError(`Failed to deal ${gameStage}. Please try again.`);
      console.error(err);
    }
  };

  const getCardImage = (card: string) => {
    // For MVP, just return a colored text representation
    const suit = card.slice(-1);
    const rank = card.slice(0, -1);
    
    let suitColor = '';
    switch (suit) {
      case '♥':
      case '♦':
        suitColor = 'text-red-500';
        break;
      case '♠':
      case '♣':
        suitColor = 'text-white';
        break;
    }
    
    return (
      <div className={`flex items-center justify-center w-12 h-16 bg-gray-800 border border-gray-600 rounded ${suitColor} font-bold`}>
        {rank}<br/>{suit}
      </div>
    );
  };

  if (isLoading && !gameState) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading game...</div>;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-red-500 text-white p-4 rounded">
          {error}
          <button 
            onClick={() => navigate('/lobby')} 
            className="block mt-4 bg-white text-red-500 px-4 py-2 rounded"
          >
            Back to Lobby
          </button>
        </div>
      </div>
    );
  }

  if (!gameState) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Game not found</div>;
  }

  return (
    <div className="min-h-screen bg-green-800 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white">Poker Table</h1>
            <p className="text-gray-200">Game #{tableId} - Stage: {gameStage}</p>
          </div>
          <div>
            <button
              onClick={() => navigate('/lobby')}
              className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600 transition"
            >
              Back to Lobby
            </button>
          </div>
        </div>

        {/* Poker table */}
        <div className="relative bg-green-900 border-8 border-brown-800 rounded-full p-12 mb-8 h-96 flex flex-col items-center justify-center">
          {/* Community cards */}
          <div className="mb-4">
            <h2 className="text-white text-center mb-2">Community Cards</h2>
            <div className="flex space-x-2 justify-center">
              {gameState.community.length > 0 ? (
                gameState.community.map((card, index) => (
                  <div key={index} className="card">
                    {getCardImage(card)}
                  </div>
                ))
              ) : (
                <div className="text-gray-300">No community cards yet</div>
              )}
            </div>
          </div>

          {/* Pot */}
          <div className="bg-gray-800 text-white px-4 py-2 rounded absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            Pot: {gameState.pot}
          </div>

          {/* AI player cards - simplified for MVP */}
          <div className="absolute top-6 left-1/2 transform -translate-x-1/2">
            <div className="text-center">
              <p className="text-white mb-1">AI Player</p>
              <div className="flex space-x-1">
                <div className="w-12 h-16 bg-blue-800 border border-blue-600 rounded"></div>
                <div className="w-12 h-16 bg-blue-800 border border-blue-600 rounded"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Player's hand */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Your Hand</h2>
          <div className="flex space-x-4">
            {username && gameState.hands[username] ? (
              gameState.hands[username].map((card, index) => (
                <div key={index} className="card">
                  {getCardImage(card)}
                </div>
              ))
            ) : (
              <p className="text-gray-300">Waiting for cards...</p>
            )}
          </div>
        </div>

        {/* Player actions */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              onClick={() => handleAction('fold')}
              className="bg-red-600 text-white px-4 py-3 rounded hover:bg-red-700 transition"
            >
              Fold
            </button>
            <button
              onClick={() => handleAction('call')}
              className="bg-blue-600 text-white px-4 py-3 rounded hover:bg-blue-700 transition"
            >
              Call {gameState.current_bet}
            </button>
            <div className="flex">
              <input
                type="number"
                min={gameState.current_bet + 1}
                value={raiseAmount}
                onChange={(e) => setRaiseAmount(parseInt(e.target.value))}
                className="w-20 px-2 py-3 text-gray-900 border border-gray-300 rounded-l focus:outline-none"
              />
              <button
                onClick={() => handleAction('raise')}
                className="bg-yellow-600 text-white px-4 py-3 rounded-r hover:bg-yellow-700 transition"
              >
                Raise
              </button>
            </div>
            <button
              onClick={handleDealNext}
              className="bg-green-600 text-white px-4 py-3 rounded hover:bg-green-700 transition"
            >
              {gameStage === 'preflop' ? 'Deal Flop' : 
               gameStage === 'flop' ? 'Deal Turn' : 
               gameStage === 'turn' ? 'Deal River' : 
               gameStage === 'river' ? 'Showdown' : 'New Game'}
            </button>
          </div>
        </div>

        {/* Game info */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-bold text-white mb-4">Game Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-gray-300">
            <div>
              <p className="font-semibold">Players:</p>
              <ul className="list-disc list-inside">
                {gameState.players.map((player, index) => (
                  <li key={index} className={gameState.active_players.includes(player) ? 'text-green-400' : 'text-red-400'}>
                    {player} {player === username && '(You)'} - Bet: {gameState.bets[player]}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-semibold">Current Bet: {gameState.current_bet}</p>
              <p className="font-semibold">Pot: {gameState.pot}</p>
            </div>
            <div>
              <p className="font-semibold">Game Stage: {gameStage}</p>
              <p className="font-semibold">Active Players: {gameState.active_players.length}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PokerTable;
