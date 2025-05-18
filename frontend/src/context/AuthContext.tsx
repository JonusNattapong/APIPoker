import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

interface AuthContextType {
  token: string | null;
  userId: number | null;
  username: string | null;
  login: (token: string, userId: number, username: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  userId: null,
  username: null,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [userId, setUserId] = useState<number | null>(
    localStorage.getItem('userId') ? parseInt(localStorage.getItem('userId') || '0') : null
  );
  const [username, setUsername] = useState<string | null>(localStorage.getItem('username'));

  const login = (token: string, userId: number, username: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('userId', userId.toString());
    localStorage.setItem('username', username);
    setToken(token);
    setUserId(userId);
    setUsername(username);
    
    // Configure axios default headers for future requests
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    localStorage.removeItem('username');
    setToken(null);
    setUserId(null);
    setUsername(null);
    
    // Remove authorization header
    delete axios.defaults.headers.common['Authorization'];
  };

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, [token]);

  return (
    <AuthContext.Provider
      value={{
        token,
        userId,
        username,
        login,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
