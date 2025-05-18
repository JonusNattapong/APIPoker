# APIPoker - Production-Ready Poker Platform

A professional online poker platform with user authentication, real-time gameplay, AI opponents, and a modern UI. This system enables players to create accounts, join tables, and play Texas Hold'em poker against AI or other players.

![APIPoker Screenshot](https://via.placeholder.com/800x400?text=APIPoker+Screenshot)

## Features

### Player Experience
- **User Authentication** - Secure registration and login system
- **Virtual Credits** - Play with virtual currency (easily extensible to real money)
- **Poker Tables** - Create and join multiple tables
- **Texas Hold'em Rules** - Standard poker gameplay with betting rounds
- **AI Opponents** - Challenge computer players with realistic behavior
- **Modern UI** - Responsive design for desktop and mobile

### Technical Features
- **REST API Backend** - FastAPI with SQLAlchemy ORM
- **React Frontend** - Modern React with TypeScript and Tailwind CSS
- **JWT Authentication** - Secure token-based auth system
- **Database Integration** - PostgreSQL for data persistence
- **Docker Support** - Easy deployment via Docker Compose
- **Extensible Architecture** - Modular design for easy feature additions

## Architecture Overview

```
APIPoker/
├── backend/             # FastAPI server
│   ├── database.py     # Database connection
│   ├── models.py       # SQLAlchemy models
│   ├── poker_logic.py  # Poker game logic
│   ├── ai_agent.py     # AI decision engine
│   ├── main.py         # API endpoints
│   └── ...
├── frontend/            # React application
│   ├── src/
│   │   ├── pages/      # Page components
│   │   ├── components/ # Reusable UI components
│   │   └── ...
│   └── ...
├── docker-compose.yml   # Docker configuration
└── ...
```

## Installation

### Prerequisites
- Docker and Docker Compose
- Node.js and npm (for local development)
- Python 3.9+ (for local development)

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/APIPoker.git
   cd APIPoker
   ```

2. Build and start the application:
   ```bash
   docker-compose up --build
   ```

3. Access the application:
   - Frontend: http://localhost:5173
   - API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Start the backend server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## How to Play

1. **Create an account** or log in if you already have one
2. **Navigate to the Lobby** to see available tables
3. **Create a new table** or join an existing one
4. **Play poker** against AI opponents:
   - Make decisions (fold, call, raise)
   - Progress through betting rounds
   - Win virtual credits by having the best hand

## API Documentation

After starting the backend server, view the interactive API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Extending the System

### Adding Payment Processing
The credit system is designed to be easily extended for real money play by integrating payment gateways like Stripe or PayPal.

### Enhancing AI Behavior
The AI agent logic in `ai_agent.py` can be improved with more sophisticated algorithms or machine learning models.

### Multi-player Support
While the current system supports playing against AI, it can be extended for multiplayer games by implementing WebSockets.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Texas Hold'em rules and poker hand evaluation algorithms
- FastAPI and React communities for excellent documentation
- All contributors to this project