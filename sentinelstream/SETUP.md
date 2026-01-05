# SentinelStream - Setup Guide

## Quick Start (SQLite - No Database Setup Required)

The easiest way to get started is using SQLite, which requires no additional setup:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python setup_database.py

# 3. Start server
python start_server.py
```

Or use the simple command:
```bash
python start_server.py
```

The server will automatically:
- Initialize SQLite database
- Create all tables
- Start on http://localhost:8000

## Using PostgreSQL (Production)

### Option 1: Docker Compose (Recommended)

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/frauddb"

# Initialize database
python setup_database.py

# Start server
python start_server.py
```

### Option 2: Local PostgreSQL

1. Install PostgreSQL
2. Create database:
```sql
CREATE DATABASE frauddb;
CREATE USER postgres WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE frauddb TO postgres;
```

3. Set environment variable:
```bash
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/frauddb"
```

4. Initialize and start:
```bash
python setup_database.py
python start_server.py
```

## Environment Variables

Create a `.env` file in the `sentinelstream` directory:

```env
# Database (optional - defaults to SQLite)
DATABASE_URL=sqlite+aiosqlite:///./sentinelstream.db

# Or for PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/frauddb

# Redis (optional - will work without it)
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT Secret (change in production!)
SECRET_KEY=your-secret-key-here

# Debug mode
DEBUG=False
```

## Verify Database Connection

After starting the server, check:
- Health endpoint: http://localhost:8000/health
- Should show "database": "connected"

## Troubleshooting

### SQLite Issues
- Make sure `aiosqlite` is installed: `pip install aiosqlite`
- Check file permissions in the project directory

### PostgreSQL Issues
- Verify PostgreSQL is running: `pg_isready`
- Check connection string format
- Ensure database exists
- Verify user permissions

### Redis Issues
- Redis is optional - server works without it
- Cache features will be disabled if Redis is unavailable

