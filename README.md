# Election Intelligence Platform

A real-time election analytics dashboard built as a data engineering, analytics, and AI portfolio project.

The project ingests live party-wise election trend data, cleans and transforms it into an analytics-ready dataset, and displays interactive insights through a Streamlit dashboard.

## Project Objective

Election result data is frequently refreshed, scattered across public result pages, and difficult to monitor manually. This project builds an automated election intelligence layer that tracks live trends, party momentum, state-level performance, close contests, and AI-assisted summaries.

## Key Features

- Automated election trend ingestion from public result pages
- Scheduled refresh every 5 minutes
- Cleaned analytics-ready CSV pipeline
- Interactive Streamlit dashboard
- State-wise party monitoring
- Party-wise leading and won trend analysis
- Close contest tracker
- Margin distribution analysis
- Raw cleaned data explorer
- Groq AI-ready summary module
- Portfolio-ready data engineering architecture

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- BeautifulSoup
- Playwright
- Groq API
- PowerShell scheduler
- CSV-based lightweight data pipeline

## Project Architecture

```text
ECI Result Pages
        ↓
Playwright / Scraper
        ↓
Raw Data Layer
        ↓
Cleaning + Transformation
        ↓
Processed CSV Layer
        ↓
Streamlit Dashboard
        ↓
AI Summary Layer
```
## Dashboard Preview

### Overview

![Overview](screenshots/overview.png)

### State Monitor

![State Monitor](screenshots/state_monitor.png)

### Close Watch

![Close Watch](screenshots/close_watch.png)

### Party Analytics

![Party Analytics](screenshots/party_analytics.png)

### AI Analyst

![AI Analyst](screenshots/ai_analyst.png)

### Data Table

![Data Table](screenshots/data_table.png)
## Folder Structure

```text
live-election-intelligence-platform/
│
├── app.py
├── scheduler.py
├── eci_party_auto_ingest.py
├── ai_insights.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── sample/
│   └── processed/
│       └── latest_results.csv
│
├── screenshots/
├── docs/
├── src/
│   ├── ai/
│   ├── pipelines/
│   ├── scraper/
│   └── utils/
```

## How to Run Locally

### 1. Create virtual environment

```bash
python -m venv venv
```

### 2. Activate virtual environment

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install
```

### 4. Run ingestion once

```bash
python eci_party_auto_ingest.py
```

### 5. Start the scheduler

```bash
python scheduler.py
```

### 6. Start the dashboard

Open a second terminal and run:

```bash
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

## Dashboard Sections

### Overview

Shows national party trend snapshot, seat trends, leading count, won count, states covered, parties tracked, and latest synced time.

### State Monitor

Tracks party-wise trend performance across states.

### Close Watch

Highlights competitive party trends based on margin-like trend differences.

### Party Analytics

Compares leading vs won values and shows state-wise party strength.

### AI Analyst

Generates structured summaries from dashboard data using Groq.

### Data Table

Displays the cleaned processed dataset used by the dashboard.

## Automation

The project includes a scheduler that refreshes election trend data every 5 minutes.

```python
REFRESH_SECONDS = 300
```

The scheduler runs separately from the Streamlit dashboard.

## Important Note

This dashboard tracks live trend counts from public election result pages. These are not final certified election results. Final results should always be verified from official ECI statistical reports.

## Portfolio Value

This project demonstrates:

- Public data ingestion
- Web scraping
- Automated refresh scheduling
- Data cleaning
- Analytics-ready pipeline design
- Dashboard development
- Interactive visual analytics
- AI-assisted reporting
- Real-time public data monitoring

## Future Improvements

- Constituency-level candidate winner tracking
- Government formation tracker
- CM candidate tracker
- Historical trend comparison
- Azure-hosted automated refresh pipeline
- Cloud database integration