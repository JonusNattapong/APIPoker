import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

interface Table {
  id: number;
  name: string;
  owner_id: number;
}

const Lobby: React.FC = () => {
  const [tables, setTables] = useState<Table[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [newTableName, setNewTableName] = useState('');
  const { username, logout } = useAuth();
  const navigate = useNavigate();

  // Fetch tables on component mount
  useEffect(() => {
    fetchTables();
  }, []);

  const fetchTables = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('http://localhost:8000/tables');
      setTables(response.data);
      setError('');
    } catch (err: any) {
      setError('Failed to fetch tables. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTableName.trim()) return;

    try {
      const response = await axios.post('http://localhost:8000/tables', { name: newTableName });
      setTables([...tables, response.data]);
      setNewTableName('');
    } catch (err: any) {
      setError('Failed to create table. Please try again.');
      console.error(err);
    }
  };

  const handleJoinTable = async (tableId: number) => {
    try {
      const response = await axios.post('http://localhost:8000/games', { table_id: tableId });
      navigate(`/table/${response.data.id}`);
    } catch (err: any) {
      setError('Failed to join table. Please try again.');
      console.error(err);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white">API Poker Lobby</h1>
            <p className="text-gray-300 mt-2">Welcome, {username}!</p>
          </div>
          <div className="flex space-x-4">
            <p className="text-green-400 font-semibold">
              Credits: 1,000
            </p>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition"
            >
              Logout
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500 text-white p-3 rounded mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-2xl font-bold text-white mb-4">Available Tables</h2>
            {isLoading ? (
              <p className="text-gray-400">Loading tables...</p>
            ) : tables.length > 0 ? (
              <div className="space-y-4">
                {tables.map(table => (
                  <div 
                    key={table.id}
                    className="flex justify-between items-center p-4 bg-gray-700 rounded hover:bg-gray-600 transition"
                  >
                    <div>
                      <h3 className="text-lg font-semibold text-white">{table.name}</h3>
                    </div>
                    <button
                      onClick={() => handleJoinTable(table.id)}
                      className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 transition"
                    >
                      Join
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400">No tables available. Create one!</p>
            )}
          </div>

          <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-2xl font-bold text-white mb-4">Create New Table</h2>
            <form onSubmit={handleCreateTable}>
              <div className="mb-4">
                <label htmlFor="tableName" className="block text-sm font-medium text-gray-300 mb-2">
                  Table Name
                </label>
                <input
                  type="text"
                  id="tableName"
                  value={newTableName}
                  onChange={(e) => setNewTableName(e.target.value)}
                  className="w-full px-3 py-2 text-gray-900 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter table name"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition"
              >
                Create Table
              </button>
            </form>
          </div>
        </div>

        <div className="mt-8 bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-2xl font-bold text-white mb-4">Game Rules</h2>
          <div className="text-gray-300 space-y-2">
            <p>• Welcome to API Poker, a Texas Hold'em poker game!</p>
            <p>• Create a table or join an existing one to play against AI opponents</p>
            <p>• Each player starts with 1,000 credits</p>
            <p>• The game follows standard Texas Hold'em rules</p>
            <p>• Make strategic decisions to win big!</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Lobby;
