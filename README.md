# Cashew Data ETL

A local Python ETL project for loading monthly transaction data from **Cashew** into **PostgreSQL**, transforming it, and preparing analytics-ready data for dashboards.

## Workflow

```text
Cashew
   │
   ▼
Monthly Data Export
   │
   ▼
Python ETL
   │
   ├── Extract
   ├── Validate
   ├── Transform
   └── Load
   │
   ▼
PostgreSQL
   │
   ▼
Dashboard-ready Data
```

## Project Structure

```text
cashew-project/
├── .env
├── pyproject.toml
├── uv.lock
├── README.md
│
├── data/
│   ├── incoming/
│   ├── processed/
│   └── rejected/
│
├── notebooks/
│
└── src/
    └── cashew/
        ├── config.py
        ├── database.py
        ├── extract.py
        ├── transform.py
        ├── validation.py
        ├── load.py
        └── pipeline.py
```

## Tech Stack

- **Python / Pandas** — ETL and data transformation
- **PostgreSQL** — Data storage and SQL transformations
- **Psycopg 3** — PostgreSQL connectivity
- **uv** — Python environment and package management
- **Jupyter** — Data exploration

## Setup

Install dependencies:

```bash
uv sync
```

Configure PostgreSQL in `.env`:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/<database>
```

The `.env` file should not be committed to Git.

## Monthly Workflow

Place each new Cashew export in:

```text
data/incoming/
```

The pipeline processes the file, validates and transforms the data, loads it into PostgreSQL, and moves the processed file to `data/processed/`.

Failed or invalid files are moved to `data/rejected/`.

PostgreSQL is organized into schemas such as:

```text
raw         → Incoming/raw data
transform   → Transformed data
```

The resulting datasets are used as the source for dashboards and reporting.
