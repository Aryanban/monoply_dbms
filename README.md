# 🎲 Monopoly Web Console

**Monopoly Digital Game Engine** | Python, Flask, MySQL, JavaScript  
*A sophisticated multiplayer board game implementation with real-time game state management and comprehensive transaction tracking*

A sophisticated digital Monopoly game engine with a modern web interface and MySQL database backend. Built with Python Flask and featuring real-time game state management, player transactions, property trading, and comprehensive game logging.

## 🎯 Project Overview

### Key Achievements
- **Implemented a complete Monopoly game engine** with multi-player support for up to 6 concurrent players
- **Designed a robust relational database architecture** using MySQL with ACID-compliant transaction management for financial operations
- **Developed a real-time web interface** using Flask backend with RESTful API and vanilla JavaScript frontend
- **Built a sophisticated trading system** with player-to-player negotiations and offer management
- **Created an admin control panel** for game state manipulation and comprehensive game event logging
- **Implemented role-based game mechanics** including property ownership, rent calculations, and financial transactions

### Technical Stack
- **Backend**: Python 3, Flask web framework
- **Frontend**: HTML5, CSS3 (modern dark theme), Vanilla JavaScript
- **Database**: MySQL 8.0 with complex schema design
- **Architecture**: RESTful API with client-side state management

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

### Key Modules & Technical Implementation

#### `monoplyapplications.py` - Game Logic & Database Layer
**Core Functions:**
- **DatabaseConnection**: MySQL connection pool with error handling and reconnection logic
- **Game State Management**: 
  - `start_game()`: Board initialization, player setup, balance allocation
  - `roll_dice()`: Dice mechanics with double detection and movement validation
- **Player Operations**:
  - `register_player()`: Player initialization with unique tokens and $1,500 starting balance
  - `eliminate_player()`: Bankruptcy handling and removal from active play
- **Property Management**:
  - `buy_property()`: Purchase validation and ownership transfer with balance checks
  - `pay_rent()`: Advanced rent calculation based on property sets and development level
  - `mortgage_property()`: Mortgage valuation and cash flow management
  - `build_house/hotel()`: Development restrictions and cost validation
- **Transaction System** (ACID-compliant):
  - `create_trade_offer()`: Player negotiation with multi-property and cash transactions
  - `record_transaction()`: Complete audit trail for all financial operations
  - `get_transaction_history()`: Detailed reporting and game analytics
- **Administrative Functions**:
  - `admin_add_property()`: Override mechanisms for testing
  - `admin_adjust_balance()`: Manual balance manipulation
  - `admin_reset_game()`: Complete game state reset

#### `app.py` - REST API Server
**API Architecture:**
- Flask application with modular blueprint routes
- RESTful API endpoints for all game operations
- Real-time state synchronization via client polling
- JSON request/response serialization
- Static asset serving (CSS, JavaScript, SVG icons)
- Jinja2 template rendering
- Error handling with HTTP status codes
- CORS headers for API access

#### Database Schema - `monopoly.sql`
**Relational Design:**
- **Games**: Session tracking (active, completed, archived states)
- **Players**: Player data, balance, position, token, status
- **Board_Spaces**: 40 properties with pricing, color sets, rental rates
- **Ownership**: Many-to-many player-property relationships with mortgage flags
- **Transactions**: Financial operations (DEBIT, CREDIT) with timestamps
- **Trades**: Offer management with status tracking (PENDING, ACCEPTED, REJECTED)
- **Logs**: Event logging (PURCHASE, RENT, TRADE, BANKRUPTCY) with precision timestamps
- **Constraints**: Foreign keys ensure referential integrity
- **Indexes**: Query optimization for real-time performance

## 🔧 Technical Challenges & Solutions

### Concurrency & Transaction Management
**Challenge**: Ensuring financial transactions remain consistent when multiple operations occur simultaneously
- **Solution**: Implemented database transaction isolation levels and row-level locking for property ownership
- **Result**: ACID compliance for all monetary operations with atomic all-or-nothing semantics

### Complex Rent Calculation Logic
**Challenge**: Dynamic rent determination based on property set monopoly, development level, and special properties
- **Solution**: Implemented property set aggregation queries and conditional rent formulas in database layer
- **Result**: Accurate rent calculations considering monopoly premiums, house/hotel multipliers, and special railroads/utilities

### Real-time Game State Synchronization
**Challenge**: Keeping client UI in sync with server state across multiple concurrent players
- **Solution**: Implemented client-side polling mechanism with delta updates and optimistic UI updates
- **Result**: Near real-time game state reflection with minimal latency and server load

### Player Bankruptcy & Game Flow
**Challenge**: Managing cascade of financial failures (player pays rent → becomes bankrupt → property transfers)
- **Solution**: Implemented transaction queue system with automatic cascade handling and audit logging
- **Result**: Seamless bankruptcy flow with complete transaction history preservation

### Database Query Optimization
**Challenge**: Complex queries joining 7+ tables for trade offers, ownership, and rent calculations
- **Solution**: Strategic indexing on foreign keys and query result caching with TTL
- **Result**: Sub-50ms response times for complex game state queries

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

## � Learning Outcomes

Through this project, I gained expertise in:

### Database Design & Management
- Designing normalized relational schemas with proper foreign key relationships
- Implementing transaction management and ACID properties in MySQL
- Query optimization through strategic indexing and JOIN operations
- Understanding database constraints and referential integrity

### Backend Development
- Building scalable REST APIs with Flask framework
- Implementing business logic for complex game mechanics
- State management across multiple client connections
- Error handling and logging for production systems

### Frontend Development
- Building interactive user interfaces with Vanilla JavaScript
- Real-time UI updates with server polling mechanisms
- CSS3 theming with CSS variables and dark mode design
- Responsive design principles for desktop and tablet interfaces

### Software Architecture
- Separating concerns between data access, business logic, and presentation layers
- Building modular and maintainable code structures
- Implementing role-based access control patterns
- Design patterns for game state management

### Problem Solving
- Complex algorithm design (rent calculation, trade negotiation)
- Concurrent system design (multi-player game synchronization)
- Performance optimization (database queries, API response times)
- Debugging distributed systems

## �👨‍💻 Author

**Aryan Bansal**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Made with ❤️ by Aryan Bansal**
