# Netflix Data Pipeline

ETL pipeline that ingests Netflix catalog data from AWS S3 into Snowflake, transforms it, and creates analytics-ready views for business intelligence.

## Architecture

```
AWS S3 (Raw CSV)
  │
  ▼
Snowflake RAW Schema (Staging)
  │  - Raw data ingestion via COPY INTO
  │  - No transformations, source-of-truth
  │
  ▼
Snowflake ANALYTICS Schema (Transformed)
  │  - Missing value handling
  │  - Date parsing and extraction
  │  - Duration normalization
  │  - Data type standardization
  │
  ▼
Analytics Views (Business-Ready)
  │  - Content by Year
  │  - Top Countries
  │  - Top Genres
  │  - Monthly Additions
  │  - Rating Distribution
  │
  ▼
Airflow DAG (Orchestration)
     - Scheduled daily
     - 4-step pipeline: Load → Transform → Views → Validate
     - Error handling and retries
```

## Tech Stack

- **AWS S3** — Data lake storage for raw files
- **Snowflake** — Cloud data warehouse for staging, transformation, and analytics
- **Apache Airflow** — Pipeline orchestration and scheduling
- **Python** — Pipeline logic and Snowflake connector
- **SQL** — Data transformation and view creation

## Pipeline Steps

### Step 1: Load Raw Data
Ingests CSV from S3 into Snowflake's RAW schema using an external stage and COPY INTO command. Snowflake automatically skips previously loaded files to prevent duplicates.

### Step 2: Transform Data
Creates a clean analytics table with:
- Missing values handled (director, cast, country filled with 'Unknown', rating with 'Not Rated')
- Date strings parsed into proper DATE type
- Year and month extracted for time-series analysis
- Duration split into numeric values (minutes for movies, seasons for TV shows)

### Step 3: Create Analytics Views
Five business-ready views built on the clean data:
- **CONTENT_BY_YEAR** — Content additions by year and type
- **TOP_COUNTRIES** — Top 15 content-producing countries (multi-value countries unnested)
- **TOP_GENRES** — Top 15 genres (multi-value genres unnested)
- **MONTHLY_ADDITIONS** — Monthly addition patterns by content type
- **RATING_DISTRIBUTION** — Rating breakdown by content type

### Step 4: Validate
Automated row count validation between RAW and ANALYTICS tables to ensure no data loss during transformation.

## Dataset

- **Source:** Netflix catalog (8,807 titles as of mid-2021)
- **Features:** 12 columns including type, title, director, cast, country, date added, release year, rating, duration, and genre
- **Storage:** AWS S3 → Snowflake

## Snowflake Schema Design

```
NETFLIX_DB
├── RAW (staging)
│   └── NETFLIX_RAW — Source data, no transformations
├── ANALYTICS (transformed)
│   ├── NETFLIX_CLEAN — Cleaned and enriched table
│   ├── CONTENT_BY_YEAR — View
│   ├── TOP_COUNTRIES — View
│   ├── TOP_GENRES — View
│   ├── MONTHLY_ADDITIONS — View
│   └── RATING_DISTRIBUTION — View
```

## Setup

### Prerequisites
- AWS account with S3 access
- Snowflake account
- Python 3.8+

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
Update `netflix_pipeline_dag.py` with your Snowflake credentials:
```python
SNOWFLAKE_CONFIG = {
    'user': 'YOUR_SNOWFLAKE_USERNAME',
    'password': 'YOUR_SNOWFLAKE_PASSWORD',
    'account': 'YOUR_SNOWFLAKE_ACCOUNT',
    'warehouse': 'NETFLIX_WH',
    'database': 'NETFLIX_DB'
}
```

### Run Pipeline
```bash
python test_pipeline.py
```

## Validation Results

```
RAW table: 8,807 rows
CLEAN table: 8,807 rows
VALIDATION PASSED: Row counts match
```
## Content Gap Analysis (Prescriptive Analytics)

K-Means clustering applied to country-genre content profiles to identify underserved market segments.

### Methodology
1. Built a country × genre matrix from Snowflake analytics views
2. Filtered to countries with 20+ titles (57 countries, 42 genres)
3. Normalized counts to percentages (content profile per country)
4. Applied K-Means clustering (K=4) to group similar markets
5. Compared each cluster's genre mix against global average to identify gaps

### Key Findings

| Cluster | Markets | Underserved Genre | Gap |
|---------|---------|-------------------|-----|
| 1 - Latin America | Argentina, Brazil, Mexico | Action & Adventure | 2.7% |
| 2 - Europe, India & SE Asia | France, Germany, India | International TV Shows | 2.8% |
| 2 - Europe, India & SE Asia | France, Germany, India | Crime TV Shows | 1.0% |
| 3 - English-speaking & East Asia | Australia, Canada, Japan | Dramas | 5.7% |
| 3 - English-speaking & East Asia | Australia, Canada, Japan | Comedies | 3.1% |

### Strategic Recommendations
1. **Latin America:** Invest in Action & Adventure content for high-growth region
2. **Europe & India:** Expand TV Show production (largest market opportunity by audience size)
3. **English-speaking & East Asia:** More localized Dramas and Comedies to drive retention

## Live Dashboard

**Streamlit App:** [Netflix Analytics Dashboard](https://netflix-data-pipeline-by-pallabisroy.streamlit.app)

Three-page interactive dashboard:
- 📊 Dashboard: Key metrics and charts from Snowflake views
- 💡 Business Insights: Six data-driven recommendations
- 🔍 Content Gap Analysis: K-Means clustering with prescriptive recommendations
- 
## Author

Pallabi S Roy
