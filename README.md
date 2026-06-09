# 🎲 Monopoly Web Console

A sophisticated digital Monopoly game engine with a modern web interface and MySQL database backend. Built with Python Flask and featuring real-time game state management, player transactions, property trading, and comprehensive game logging.

## ✨ Features

### Core Gameplay
- **Multi-player Support**: Play with up to 6 players simultaneously
- **Board System**: 40-space board with international properties (Brazil, Israel, Italy, Germany, China, France, UK, USA)
- **Property Management**: Buy, sell, mortgage, and develop properties with houses and hotels
- **Financial System**: Complete transaction tracking including rent payments, taxes, and special fees
- **Dice Rolling**: Realistic dice mechanics with double detection

### Property System
- **8 Property Sets**: Each with unique color-coding and pricing
- **Airports & Companies**: Special properties with unique mechanics
- **Development**: Build houses and hotels on owned properties
- **Mortgaging**: Strategic property mortgaging for cash flow management

### Trading & Negotiation
- **Player-to-Player Trades**: Propose and accept trades with properties and cash
- **Trade Management**: Accept, reject, or modify trade offers in real-time
- **Pending Trades Panel**: Visual display of all incoming trade offers

### Game Administration
- **Admin Panel**: Control game state, manage players, and manipulate board
- **Player Management**: Add/remove players, adjust balances, eliminate players
- **Property Control**: Admin override for adding/removing properties
- **Game History**: Complete event logging and transaction tracking

### Modern UI
- **Dark Theme**: Eye-friendly dark interface with gold accents
- **Real-time Updates**: Live board state, player statistics, and game events
- **Responsive Design**: Works seamlessly on desktop and tablet
- **Visual Feedback**: Animations for purchases, trades, and significant events
- **Game Logging**: Comprehensive game event log with timestamps

## 🏗️ Architecture

### Frontend
- **HTML5** with semantic structure
- **CSS3** with CSS variables for theming
- **Vanilla JavaScript** for dynamic interactions
- **Icon System**: SVG icons for actions (dice, houses, hotels, trades)

### Backend
- **Python 3** with Flask web framework
- **MySQL Database** with robust schema design
- **RESTful API** for all game operations
- **Transaction Management**: ACID compliance for financial operations

### Database Schema
- **Games**: Track all active and completed games
- **Players**: Player data, balance, and properties
- **Board Spaces**: Property definitions and board state
- **Ownership**: Property ownership relationships
- **Transactions**: Complete audit trail of all money movements
- **Trades**: Offer and trade history
- **Logs**: Comprehensive event logging

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- MySQL 8.0 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Aryanban/monoply_dbms.git
   cd monoply_dbms
   ```

2. **Create a Python virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install flask mysql-connector-python
   ```

4. **Set up the database**
   ```bash
   mysql -u root -p < monopoly.sql
   ```

5. **Configure database connection**
   Edit `monoplyapplications.py` and update the database credentials:
   ```python
   DatabaseConnection(
       host='localhost',
       user='your_mysql_user',
       password='your_password',
       database='monopoly_db'
   )
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Open in browser**
   Navigate to `http://localhost:5000`

## 📖 Usage

### Starting a Game
1. Click "New Game" button to create a fresh game
2. Register players through the Admin Hub
3. Click "Start Turn" to begin gameplay

### During Gameplay
- **Roll Dice**: Click the Roll button to move
- **View Stats**: Check player statistics and balances
- **Trade Properties**: Click Trade to negotiate with other players
- **End Turn**: Complete your turn and pass to the next player
- **View Properties**: See all owned properties and available actions

### Admin Functions
- **Add/Remove Players**: Manage player participation
- **Adjust Balances**: Override player cash for testing
- **Manage Properties**: Add or remove properties from players
- **Eliminate Players**: Remove bankrupt players from the game
- **Reset Game**: Start fresh with current board state
- **End/Delete Game**: Conclude or completely remove a game

## 🛠️ Development

### Project Structure
```
monopoly/
├── app.py                    # Flask application and API routes
├── monoplyapplications.py   # Game logic and database operations
├── monopoly.sql             # Database schema and sample data
├── static/
│   ├── style.css           # Modern dark theme stylesheet
│   └── script.js           # Frontend game logic
├── templates/
│   └── index.html          # Main game interface
└── icons/                  # SVG icons for UI elements
    ├── dice-svgrepo-com.svg
    ├── house-svgrepo-com.svg
    ├── hotel-svgrepo-com.svg
    ├── mortgage-insurance-svgrepo-com.svg
    ├── stats-1370-svgrepo-com.svg
    └── swap-svgrepo-com.svg
```

### Key Modules

#### `monoplyapplications.py`
- **DatabaseConnection**: MySQL connection management
- **start_game()**: Initialize a new game
- **roll_dice()**: Execute dice roll and movement
- **register_player()**: Add player to game
- **buy_property()**: Handle property purchases
- **pay_rent()**: Calculate and process rent payments
- **create_trade_offer()**: Manage trade negotiations
- **record_transaction()**: Log financial transactions
- **admin_*()**: Administrative override functions

#### `app.py`
- Flask server setup
- API endpoints for all game operations
- WebSocket-style polling for real-time updates
- Static file serving
- Template rendering

## 🎮 Game Rules

### Movement
- Players start at GO (index 0)
- Roll dice to move around the board
- Pass GO to collect $200
- Landing on Jail is optional (can choose to stay or pay bail)

### Property Purchase
- Buy landed property for the listed price
- Cannot buy properties already owned
- Properties show ownership and development status

### Rent & Payments
- Pay rent to property owner (owner cannot be charged)
- Rent varies based on property development
- Utilities and Railroads have special rent calculations

### Trading
- Players can propose trades to any other player
- Trades can include properties and/or cash
- Both parties must accept for trade to execute

### Winning
- Last player with money remaining wins
- Bankrupt players are eliminated
- Game continues until one player remains

## 🎨 Customization

### Theme Variables
Edit `static/style.css` CSS variables section:
```css
:root {
  --bg: #0f1117;           /* Background color */
  --panel: #181c26;        /* Panel backgrounds */
  --text: #e7ecf3;         /* Text color */
  --accent: #4f46e5;       /* Accent color */
  --gold: #d4af37;         /* Gold highlights */
  --danger: #ef4444;       /* Error/danger color */
}
```

### Player Colors
Modify the `tokenColors` array in `static/script.js` to change player token colors.

## 🐛 Troubleshooting

### Database Connection Error
- Verify MySQL is running
- Check credentials in `monoplyapplications.py`
- Ensure `monopoly_db` database exists

### Port Already in Use
```bash
# Run on different port
python app.py --port 5001
```

### Module Not Found
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

## 📊 API Endpoints

### Game Management
- `GET /api/games` - List all games
- `POST /api/games` - Create new game
- `GET /api/games/<id>` - Get game details
- `POST /api/games/<id>/start-turn` - Start player turn

### Player Operations
- `GET /api/players` - List players in current game
- `POST /api/players` - Register new player
- `GET /api/players/<id>` - Get player details

### Game Actions
- `POST /api/roll` - Roll dice and move
- `POST /api/buy-property` - Purchase property
- `POST /api/trade` - Create trade offer
- `POST /api/end-turn` - End current turn

### Admin Operations
- `POST /api/admin/add-property` - Add property to player
- `POST /api/admin/remove-property` - Remove property
- `POST /api/admin/adjust-balance` - Change player balance
- `POST /api/admin/eliminate-player` - Eliminate player

## 📝 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

**Aryan Bansal**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ by Aryan Bansal**
