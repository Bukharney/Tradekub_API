# TradeKub API

TradeKub API is an online trading backend service built with Python, FastAPI, and SQLAlchemy.

## Features

- **User Authentication**: Secure JWT-based authentication (`/login`, `/logout`).
- **Account & Portfolio Management**: Track cash balance, line available, credit limits, and stock holdings.
- **Order Engine**: Real-time limit order placement (`Buy`/`Sell`), cancellation, and automatic matching engine.
- **Banking Transactions**: Deposit and withdrawal management.
- **Stock Market Data**: Real-time price info, bid/offer depth, historical candlesticks, and search.
- **Dividends & Turnover**: Financial statement metrics and dividend tracking.
- **Analytics & Notifications**: Market activity insights and automated user alerts.

---

## Local Setup & Quick Start

### 1. Requirements
- Python 3.10+
- Virtual environment (`venv`)

### 2. Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/Bukharney/Tradekub_api.git
cd Tradekub_api

# Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to create your local `.env` file:

```bash
cp .env.example .env
```

Default local `.env` setup uses SQLite (`tradekub.db`):
```env
DATABASE_URL=sqlite:///./tradekub.db
SECRET_KEY=local_dev_secret_key_change_in_production_1234567890
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
HOST=127.0.0.1
PORT=8000
```

*(To use PostgreSQL instead, update `DATABASE_URL=postgresql://username:password@localhost:5432/tradekub`)*.

---

### 4. Running the Local Server

Run the automated local startup script:

```bash
python run_local.py
```

Or start directly with Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

### 5. API Documentation

Once the server is running, access the interactive API documentations at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### 6. Running Tests

Run the full automated pytest test suite:

```bash
python -m pytest tests/ -v
```

---

## License

TradeKub is open-source software licensed under the [MIT License](LICENSE).
