# 🏢 AI Real Estate Pipeline — Enterprise Underwriting & GIS Intelligence

[![CI Quality Gate](https://github.com/jraphaelbarbosa/AI_Real_Estate_Pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/jraphaelbarbosa/AI_Real_Estate_Pipeline)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Contracts](https://img.shields.io/badge/Contracts-Pydantic%20v2-red)
![Tests](https://img.shields.io/badge/Tests-11%20passed-brightgreen)
![Orchestration](https://img.shields.io/badge/Orchestration-LangChain-orange.svg)
![LLM](https://img.shields.io/badge/LLM-OpenAI%20GPT--4o--mini-green.svg)
![Integration](https://img.shields.io/badge/Integration-Monday.com%20GIS%20GraphQL-purple.svg)

> **[ 🇧🇷 Ler em Português ](README.pt-br.md)**

> **Executive Overview:** The **AI Real Estate Pipeline** is an enterprise autonomous agent engineered for **real estate brokerages and property investment funds**. The platform crawls and normalizes disparate property listings from across the web, generates an objective, **apples-to-apples price/sqm and renovation ROI comparison**, geocodes exact coordinates via Nominatim GIS, and synchronizes deals into **Monday.com Enterprise Work OS**—complete with interactive map views and automated lead routing to the nearest field broker.

---

## 🎯 Commercial Value: Standardized Deal Benchmarking & Broker Routing

* **The Problem:** Property investors and real estate agencies waste 15+ hours weekly sifting through fragmented, non-standardized listing descriptions across multiple portals. Determining whether a property is underpriced, calculating renovation viability, and assigning it to the right local agent is manual, slow, and error-prone.
* **Apples-to-Apples Benchmarking:** The pipeline ingests unstructured property data and extracts standardized valuation parameters: square footage, structural condition, estimated renovation costs, and **After Repair Value (ARV)** to output a clear investment verdict (`BUY`, `PASS`, or `INVESTIGATE`).
* **Interactive GIS Mapping & Nearest-Broker Routing:** Addresses are automatically geocoded into precise latitude/longitude pairs via Geopy Nominatim, rendering an interactive Map View on Monday.com and routing promising deals directly to the closest field broker for immediate inspection.
* **Commercial Impact:** Eliminates 80% of manual listing screening time, standardizes underwriting criteria across the entire investment team, and reduces field broker response time from days to minutes.

---

## 🏗️ 1. System Architecture & Data Flow

```mermaid
flowchart TD
    A[Raw Property Listing Scraping] --> B[1. Fault-Tolerant JSON Ingestor]
    B -->|Validated PropertyInput| C[2. Geospatial Resolver - Geopy Nominatim]
    C -->|Lat/Lng Coordinates| D[3. Cognitive Underwriter - LangChain & GPT-4o-mini]
    D -->|Strict Financial Output| E[4. Pydantic PropertyAnalysis Validation]
    E --> F[5. Monday.com GraphQL Client]
    F --> G[Interactive Enterprise Map View]
    F --> H[Executive Deal Pipeline Board]
    F --> I[Automated Nearest-Broker Dispatch]
```

---

## 🛡️ 2. Enterprise Reliability & Design Decisions

### ⚡ Graceful Degradation & Mock Fallback
* If external LLM endpoints experience rate limiting (`RateLimitError`) or connection timeouts, the system automatically degrades into deterministic heuristic evaluation mode (`mock_mode`), preventing batch ingestion stops.
* The test suite runs with **100% deterministic mocks** without requiring live OpenAI API keys or incurring token spend.

### 📐 Strict Financial Invariants (Pydantic v2)
* Financial models enforce strict valuation bounds:
  * **ARV (After Repair Value):** Enforced multiplier rules against purchase prices.
  * **Renovation Estimation:** Parametric ratio checking against historical submarket baselines.
  * **Viability Scoring:** Bounded integer metrics (`0 <= score <= 100`) coupled with explicit action enumerations (`BUY`, `PASS`, `INVESTIGATE`).

### 🗺️ GIS Location Intelligence & Routing
* Automatically geocodes arbitrary address strings into precise latitude/longitude pairs, formatting GraphQL payloads specifically for Monday.com's native interactive map views and enabling distance-based dispatch to local agents.

---

## 🧪 3. Automated Testing & CI Quality Gate

The pipeline includes a unit test suite covering schema validation, fault tolerance, analyzer mock mode, and Monday GraphQL payload construction.

```bash
# Run test suite with coverage
pytest tests/ -v --cov=src

# Run linter
ruff check src/ tests/
```

---

## 🚀 4. Quickstart & Local Execution

### Prerequisites
* Python 3.11+
* OpenAI API Key (optional for mock mode)
* Monday.com API Key (optional for dry-run mode)

### Setup
```bash
# 1. Clone repository
git clone https://github.com/jraphaelbarbosa/AI_Real_Estate_Pipeline.git
cd AI_Real_Estate_Pipeline

# 2. Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Execute pipeline
python -m src.main
```

---

## 📂 5. Canonical Repository Structure

```text
AI_Real_Estate_Pipeline/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Automated CI Quality Gate (ruff + pytest)
├── data/
│   └── raw_mock_data.json             # Property dataset fixture
├── src/
│   ├── config.py                      # Environment configuration
│   ├── main.py                        # Pipeline entrypoint
│   ├── domain/
│   │   └── schemas.py                 # Pydantic v2 Strict Data Contracts
│   ├── services/
│   │   ├── ingestor.py                # Fault-tolerant JSON file ingestion
│   │   ├── analyzer.py                # LangChain & OpenAI Underwriter
│   │   └── monday.py                  # Monday.com GraphQL Client
│   └── utils/
│       ├── geocoder.py                # Geopy Nominatim Location Resolver
│       └── logger.py                  # Structured logging module
├── tests/
│   ├── conftest.py                    # Pytest Global Fixtures
│   └── unit/
│       ├── test_domain_schemas.py     # Pydantic contract tests
│       ├── test_ingestor.py           # Ingestion fault tolerance tests
│       ├── test_analyzer.py           # Underwriter & fallback tests
│       └── test_monday.py             # Monday.com GraphQL mock tests
├── requirements.txt                   # Production & testing dependencies
└── README.md                          # Technical platform documentation
```
