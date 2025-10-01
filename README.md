# Healthcare Cost Navigator API

A FastAPI-based web service that enables patients to search for hospitals offering MS-DRG procedures, view estimated prices & quality ratings, and interact with an AI assistant for natural language queries.
<p align="center">
  <img src="example.gif" alt="Demo" width="600"/>
</p>

---

## 🚀 Features

- **Provider Search:** Search hospitals by DRG code/description within a geographic radius
- **Cost Comparison:** View and compare estimated healthcare costs across providers
- **Quality Ratings:** Access hospital quality ratings (1-10 scale)
- **AI Assistant:** Natural language interface for complex healthcare queries
- **Geographic Search:** PostGIS-powered spatial queries for accurate distance calculations
- **RESTful API:** Clean, well-documented REST endpoints

---

## 📋 Prerequisites

- Docker & Docker Compose
- OpenAI API Key (for AI assistant functionality)
- 4GB+ RAM recommended
- PostgreSQL with PostGIS extension (handled by Docker)

---

## 🛠️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd healthcare-cost-navigator
   ```
2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```
3. **Build and start the services**
   ```bash
   docker-compose up --build -d
   ```
4. **Initialize the database**
   ```bash
   docker-compose exec app python scripts/init_db.py
   ```
5. **Load the data (ETL)**
   ```bash
   docker-compose exec app python -m etl.etl --csv data/med_data_sample.csv
   ```
6. **Verify installation**
   ```bash
   # Check API health
   curl http://localhost:8000/health

   # Run tests
   docker-compose exec app python tests/test_all.py
   ```

7. **Access the User Interface**
   Open your browser and go to [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html) to use the web UI for searching providers and interacting with the AI assistant.

---

## 📖 API Documentation

Once running, access the interactive API documentation at:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔍 API Endpoints

### Provider Search

```bash
GET /providers?drg={drg}&zip={zip}&radius_km={radius}
```
Search for healthcare providers by DRG and location.

**Example:**
```bash
curl "http://localhost:8000/providers?drg=470&zip=10001&radius_km=50"
```
**Response:**
```json
{
  "total_results": 15,
  "search_params": {
    "drg": "470",
    "zip_code": "10001",
    "radius_km": 50
  },
  "providers": [
    {
      "rndrng_prvdr_org_name": "Hospital for Special Surgery",
      "rndrng_prvdr_city": "New York",
      "avg_submtd_cvrd_chrg": 75000.00,
      "overall_rating": 9.2,
      "distance_km": 3.5
    }
  ]
}
```

### AI Assistant

```bash
POST /ask
```
**Example:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the cheapest hospital for knee replacement near 10001?"}'
```
**Response:**
```json
{
  "answer": "The cheapest hospital for knee replacement (DRG 470) within your search area is Mount Sinai Hospital in New York, NY, with an average charge of $68,500. It has a rating of 8.5/10 and is located 2.3 miles from ZIP code 10001.",
  "sql_query": "SELECT * FROM providers WHERE...",
  "confidence": 0.85,
  "results_count": 5
}
```

---

## 🤖 AI Assistant Example Prompts

Here are some example prompts and why each is useful:

- **"Find DRG 872 providers near ZIP 78852 sorted by cost"**
  *Demonstrates searching for a specific DRG code in a geographic area, sorted by price—useful for patients seeking the most affordable care for a particular procedure.*

- **"Show me the most affordable respiratory treatments  in Arkansas"**
  *Highlights state-wide cost comparison for a treatment category, helping users find the best value across a region.*

- **"What are the highest rated hospitals for Sepsis Treatment?"**
  *Focuses on quality by identifying top-rated hospitals for a specific condition, supporting users who prioritize care quality.*

- **"Compare costs for Sepsis treatment in Texas"**
  *Enables side-by-side cost comparison for a treatment within a state, empowering users to make informed financial decisions.*

- **"List hospitals with above 1 ratings in OK"**
  *Shows how to filter hospitals by minimum quality rating in a state, useful for quickly identifying acceptable care options.*

---

## 📊 Database Schema

**Main Tables:**

- `providers`: Healthcare provider information and costs
- `provider_ratings`: Quality ratings (1-10 scale)
- `zip_codes`: Geographic data with lat/lon coordinates

**Key Features:**

- PostGIS spatial indexing for efficient geographic queries
- Full-text search on DRG descriptions
- Optimized indexes for common query patterns

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  PostgreSQL │────▶│   PostGIS   │
│     API     │     │   Database  │     │   Spatial   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                        │
       ▼                                        │
┌─────────────┐                                │
│   OpenAI    │                                │
│     GPT     │◀───────────────────────────────┘
└─────────────┘
```

**Technology Stack:**

- Python 3.11
- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy (async ORM)
- OpenAI GPT-4
- Docker

---

## 🧪 Testing

```bash
# Run all tests
docker-compose exec app python tests/test_all.py

# Run specific test modules
docker-compose exec app python tests/test_providers_api.py
docker-compose exec app python tests/test_ask_api.py
```

---

## 📈 Performance Considerations

- Spatial indexes with GIST for fast radius searches
- Text search using GIN + pg_trgm for fuzzy DRG matching
- Connection pooling with async SQLAlchemy
- Limited result sets and efficient joins
- ZIP code coordinates cached during ETL

---

## 🚦 Monitoring

```bash
# API health check
curl http://localhost:8000/health

# Database statistics
docker-compose exec postgres psql -U postgres -d healthcare_db -c "
  SELECT 'Providers' as table, COUNT(*) as count FROM providers 
  UNION SELECT 'Ratings', COUNT(*) FROM provider_ratings 
  UNION SELECT 'ZIP Codes', COUNT(*) FROM zip_codes;"
```

**View logs:**
```bash
docker-compose logs -f app
```

---

## 🛠️ Development

### Useful Commands

```bash
# Enter Python shell with app context
docker-compose exec app python

# Database shell
docker-compose exec postgres psql -U postgres -d healthcare_db

# Reset and reload data
docker-compose exec app python -m etl.etl --csv data/med_data_sample.csv --reset

# Format code
docker-compose exec app black .
docker-compose exec app isort .
```

### Project Structure

```
healthcare-cost-navigator/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── routers/
│   │   ├── providers.py     # Provider endpoints
│   │   └── ask.py           # AI assistant endpoint
│   └── services/
│       ├── provider_service.py
│       ├── location_service.py
│       └── ai_service.py
├── etl/
│   └── etl.py               # ETL pipeline
├── tests/
│   └── test_all.py          # Test suite
├── migrations/
│   └── 001_initial_schema.sql
├── data/
│   └── med_data_sample.csv
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🔒 Security Considerations

- SQL injection prevention in AI-generated queries
- Input validation on all endpoints
- Rate limiting ready (configure in production)
- Environment-based configuration
- Secure OpenAI API key handling
