# Biothreat Radar

Biosurveillance fusion dashboard pulling real data from NWSS, CDC Traveler Genomic Surveillance, and SecureBio Detection — overlaid on a shared map and timeline with automated anomaly detection.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite + React-Leaflet + Recharts |
| Backend | FastAPI + SQLAlchemy 2 + asyncpg |
| Database | PostgreSQL |
| Pipeline | Daily cron via APScheduler / Render Cron |
| Deployment | Render (free tier) |

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running locally (or use Docker: `docker run -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres`)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # Mac/Linux
# Edit .env — set DATABASE_URL to your local postgres

# Create database
psql -U postgres -c "CREATE DATABASE biothreat;"

# Run the API
uvicorn app.main:app --reload --port 8000
```

The API starts at http://localhost:8000. Tables are created automatically on first run.

**Trigger the first pipeline pull** (populates the database):
```bash
curl -X POST http://localhost:8000/api/pipeline/run
```
Or visit http://localhost:8000/docs and use the Swagger UI.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard opens at http://localhost:5173.

---

## Deploy to Render

### 1. Push to GitHub

```bash
cd C:\Users\tloftis\biothreat-radar
git init
git add .
git commit -m "initial commit"
gh repo create biothreat-radar --public
git push -u origin main
```

### 2. Create Render resources

1. Go to [render.com](https://render.com) → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render reads `render.yaml` and creates:
   - `biothreat-db` — PostgreSQL database
   - `biothreat-api` — FastAPI backend
   - `biothreat-frontend` — React static site
   - `biothreat-pipeline` — Daily 06:00 UTC cron job

### 3. Set secrets in Render dashboard

After the Blueprint deploys, go to **biothreat-api** → **Environment** and set:

| Key | Value |
|-----|-------|
| `SOCRATA_APP_TOKEN` | (optional) Your CDC Socrata token — get one free at data.cdc.gov |

### 4. Trigger the first sync

In the Render dashboard → **biothreat-api** → open the API URL → append `/api/pipeline/run` and POST to it.
Or click **Sync Now** in the dashboard UI once it's live.

### 5. Update CORS

Once you know your frontend URL, update `CORS_ORIGINS` in the biothreat-api env vars:
```
["https://biothreat-frontend.onrender.com"]
```

---

## Data Sources

| Source | Endpoint | Cadence | Notes |
|--------|----------|---------|-------|
| NWSS | `data.cdc.gov/resource/2ew6-ywp6.json` | Weekly (Fridays) | ~3,000 WWTP sites, SARS-CoV-2 |
| TGS Variants | `data.cdc.gov/resource/jr58-6ysp.json` | Weekly | National variant proportions; airport-level when available |
| SecureBio | `securebio.org` public dashboard | Quarterly | 13 metagenomic sites; site presence always shown |

---

## Anomaly Detection

Each pipeline run recomputes z-scores across all (site, metric) pairs using an 8-week rolling baseline window. Signals where |z| ≥ 2.0 are flagged as anomalies and appear in the dashboard alert table and as red markers on the map.

The threshold and window are configurable via environment variables:
- `ANOMALY_WINDOW_WEEKS` (default: 8)
- `ANOMALY_THRESHOLD` (default: 2.0)
