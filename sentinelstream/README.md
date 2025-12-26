# SentinelStream - Real-Time Fraud Detection Engine

A high-performance, production-ready fraud detection system built with FastAPI, PostgreSQL, Redis, and Machine Learning.

## Features

- ⚡ **High-Performance**: Processes transactions in under 200ms
- 🔒 **Fraud Detection**: Multi-layered approach with Rule Engine + ML Model
- 🔑 **Idempotency**: Prevents duplicate transactions
- 🚀 **Async Tasks**: Non-blocking webhooks and email alerts via Celery
- 🔐 **JWT Authentication**: Secure API access
- 📊 **Rate Limiting**: Built-in rate limiting with FastAPI-Limiter
- 🐳 **Docker Ready**: Full Docker Compose setup
- 📈 **Load Tested**: Validated with Locust for 100+ req/s

## Architecture

- **FastAPI**: High-concurrency ASGI API framework
- **PostgreSQL**: Immutable transaction ledger with ACID compliance
- **Redis**: Caching and session management
- **Celery**: Asynchronous task queue for webhooks and alerts
- **Scikit-Learn**: Isolation Forest model for anomaly detection
- **Nginx**: Reverse proxy and load balancer

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker Compose

1. Clone the repository and navigate to the project:
```bash
cd sentinelstream
```

2. Start all services:
```bash
docker-compose up -d
```

3. Initialize the database:
```bash
docker-compose exec api python -c "from app.db import init_db; import asyncio; asyncio.run(init_db())"
```

4. Access the API:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start PostgreSQL and Redis (using Docker or locally):
```bash
docker-compose up -d postgres redis
```

4. Initialize database:
```bash
python -c "from app.db import init_db; import asyncio; asyncio.run(init_db())"
```

5. Start the API server:
```bash
uvicorn app.main:app --reload
```

6. Start Celery worker (in a separate terminal):
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

## API Endpoints

### Transaction Processing

**POST /transaction**
Process a transaction with fraud detection.

Request:
```json
{
  "user_id": "user123",
  "amount": 100.0,
  "currency": "USD",
  "location": "New York, NY",
  "merchant_id": "merchant456",
  "transaction_type": "purchase",
  "idempotency_key": "unique-key-123",
  "metadata": {}
}
```

Response:
```json
{
  "transaction_id": "uuid",
  "status": "approved",
  "is_fraud": false,
  "risk_score": 0.15,
  "rule_score": 0.1,
  "ml_score": 0.18,
  "message": "Transaction processed successfully",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### User Balance

**GET /balance/{user_id}**
Get user's current balance.

### Transaction History

**GET /history/{user_id}?page=1&page_size=20**
Get user's transaction history with pagination.

### Fraud Rules Management

**POST /rules**
Create a new fraud detection rule (requires authentication).

**GET /rules**
List all fraud detection rules (requires authentication).

### Authentication

**POST /token**
Get JWT access token.

## Fraud Detection

### Rule Engine

The Rule Engine allows you to define dynamic fraud detection rules stored in the database. Rules can include conditions like:

```json
{
  "rule_name": "High Amount Alert",
  "rule_condition": {
    "field": "amount",
    "operator": ">",
    "value": 5000
  },
  "rule_actions": {
    "risk_score": 0.8,
    "flag": true
  },
  "priority": 10,
  "is_active": true
}
```

### ML Model

The system uses an Isolation Forest model for anomaly detection. The model scores transactions based on:
- Transaction amount
- Time patterns (hour, day)
- Amount deviation from user average
- Location differences
- Transaction frequency

### Final Risk Score

The final risk score is a weighted combination:
```
final_risk_score = (rule_score * 0.4) + (ml_score * 0.6)
```

Transactions with risk_score > 0.7 are flagged as fraud.
Transactions with risk_score > 0.8 are automatically declined.

## Testing

Run the test suite:

```bash
pytest tests/ -v --cov=app --cov-report=html
```

Run load tests with Locust:

```bash
locust -f tests/locustfile.py
```

## Performance

- **Latency Target**: < 200ms per transaction
- **Throughput**: 100+ requests/second
- **Concurrency**: Async/await with FastAPI

## Deployment

### Production Checklist

1. ✅ Set strong `SECRET_KEY` in environment
2. ✅ Configure PostgreSQL with proper credentials
3. ✅ Set up SSL certificates for Nginx
4. ✅ Configure proper rate limits
5. ✅ Set up monitoring and logging
6. ✅ Train and deploy production ML model
7. ✅ Configure email service (SendGrid/SES) for alerts
8. ✅ Set up backup strategy for PostgreSQL

### Environment Variables

See `.env.example` for all configuration options.

## Security

- JWT-based authentication
- Password hashing with bcrypt
- SQL injection prevention with SQLAlchemy ORM
- Rate limiting to prevent abuse
- Idempotency keys to prevent duplicate processing
- Input validation with Pydantic

## License

Proprietary - Zaalima Development Pvt. Ltd.

