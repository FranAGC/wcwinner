# WC Winner 2026 🏆

Predictive engine and simulation platform for the 2026 FIFA World Cup. It uses Bivariate Poisson distributions and time-decay ELO ratings to simulate matches and advance through the 48-team bracket.

## Tech Stack
- **Database**: DuckDB (Persistent via `football_probability.duckdb`)
- **Backend**: FastAPI, Polars (for high-speed OLAP & ETL), Numpy
- **Frontend**: React 18, Vite, TypeScript, Lucide React
- **Algorithms**: Bivariate Poisson (Attack/Defense Strength), ELO Rating System

## Installation & Setup

```bash
# 1. Setup Backend Environment
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. Setup Frontend Environment
cd frontend
npm install
```

## Data Seeding

The platform relies on a static local database initialized via CSV backups (`backend/data/*.csv`).
You must initialize the database before running simulations:

- **Quick Seed (WC26 Only)**: `python backend/scripts/seed_wc26.py` (Resets and inserts the 72 official group matches).
- **Full ETL (Restore from CSV)**: `python backend/scripts/run_etl.py` (Completely wipes the database and restores all historical stats, ELOs, and features from local CSV files).

## Running the Application

Open two terminal instances:

```bash
# Terminal 1: Backend API
.venv\Scripts\python -m backend.api.main
# Server runs on http://0.0.0.0:8000
```

```bash
# Terminal 2: Frontend Vite Server
cd frontend
npm run dev
# App runs on http://localhost:5173
```

## API Structure (Key Endpoints)
- `POST /simulate/phase`: Simulates all unplayed matches in a specific phase using Poisson expectations.
- `POST /simulate/advance`: Advances qualified teams to the next bracket round (e.g., handling best 3rd-place logic).
- `POST /reset/wc26`: Triggers the fast re-seed of the WC26 tournament.
- `POST /reset/all`: Triggers the full database ETL pipeline.
