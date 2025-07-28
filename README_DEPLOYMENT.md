# FIFO COGS System - Deployment Guide

## Overview

Complete multi-tenant FIFO COGS calculation system with:
- **Journaled runs** with full audit trail and rollback support
- **REST API** built with FastAPI
- **React dashboard** with Supabase authentication
- **CLI tools** for local operations
- **Multi-tenant isolation** with Row Level Security

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React App     │───▶│   FastAPI       │───▶│   Supabase      │
│   (Vercel)      │    │   (Render/Fly)  │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Local Development

### Prerequisites
- Python 3.8+
- Node.js 18+
- Supabase account

### 1. Backend Setup

```bash
# Install Python dependencies
pip install fastapi uvicorn pandas supabase python-dotenv

# Set environment variables
export SUPABASE_URL="your_supabase_project_url"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"

# Run the API server
cd api/
python app.py
# Server runs on http://localhost:8000
```

### 2. Database Setup

Run the migration in Supabase SQL Editor:

```sql
-- Copy and paste contents of infra/migrations/001_create_multi_tenant_schema.sql
```

### 3. Frontend Setup

```bash
cd cogs-dashboard/

# Install dependencies
npm install

# Set environment variables
export REACT_APP_SUPABASE_URL="your_supabase_project_url"
export REACT_APP_SUPABASE_ANON_KEY="your_anon_key"
export REACT_APP_API_BASE_URL="http://localhost:8000"

# Start development server
npm start
# App runs on http://localhost:3000
```

### 4. CLI Usage

```bash
# Run COGS calculation
python -m app.cli run --tenant-id my-company --sales-file golden/golden_sales_clean.csv --dry-run

# Rollback a run
python -m app.cli rollback run_123 --confirm

# List runs
python -m app.cli list-runs --tenant-id my-company

# Generate journal entry
python -m app.cli journal-entry run_123 --format csv --output-file journal.csv
```

## Production Deployment

### 1. Deploy FastAPI Backend

#### Option A: Render

Create a new web service on Render:

```yaml
# render.yaml
services:
  - type: web
    name: fifo-cogs-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python api/app.py"
    envVars:
      - key: SUPABASE_URL
        value: your_supabase_project_url
      - key: SUPABASE_SERVICE_ROLE_KEY
        value: your_service_role_key
      - key: PORT
        value: 8000
```

#### Option B: Fly.io

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "api/app.py"]
```

```bash
# Deploy to Fly.io
fly launch
fly secrets set SUPABASE_URL="your_url" SUPABASE_SERVICE_ROLE_KEY="your_key"
fly deploy
```

### 2. Deploy React Frontend to Vercel

```bash
cd cogs-dashboard/

# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod

# Set environment variables in Vercel dashboard:
# REACT_APP_SUPABASE_URL
# REACT_APP_SUPABASE_ANON_KEY
# REACT_APP_API_BASE_URL (your FastAPI deployment URL)
```

Or deploy via Vercel Dashboard:
1. Connect your GitHub repository
2. Set build command: `npm run build`
3. Set output directory: `build`
4. Add environment variables

### 3. Configure Environment Variables

#### Vercel (Frontend)
```
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your_anon_key
REACT_APP_API_BASE_URL=https://your-api-deployment.render.com
```

#### Render/Fly (Backend)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
PORT=8000
DEBUG=false
```

### 4. Supabase Configuration

1. **Authentication**: Enable email/password auth in Supabase Dashboard
2. **RLS**: Already configured in migration (Row Level Security enabled)
3. **API Keys**: 
   - Use **anon key** for frontend (public)
   - Use **service role key** for backend (private)

## Quick Smoke Tests

### API Health Check
```bash
curl https://your-api-url.com/health
# Expected: {"status": "healthy", "service": "fifo-cogs-api"}
```

### Create a Run
```bash
curl -X POST https://your-api-url.com/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "mode": "fifo",
    "sales_data": [],
    "lots_data": []
  }'
```

### List Runs
```bash
curl "https://your-api-url.com/api/v1/runs?tenant_id=test-tenant"
```

### Rollback a Run
```bash
curl -X POST https://your-api-url.com/api/v1/runs/{run_id}/rollback
```

### Get Journal Entry
```bash
curl "https://your-api-url.com/api/v1/runs/{run_id}/journal-entry?format=csv"
```

## Testing

### Run All Tests
```bash
# Backend tests
python -m pytest tests/ -v

# Specific test suites
python -m pytest tests/unit/ -v                    # Unit tests
python -m pytest tests/integration/ -v             # Integration tests
python -m pytest tests/integration/test_e2e_dashboard.py -v  # E2E tests
```

### Test Results Summary
- **Unit tests (9)**: Core FIFO logic validation
- **Integration tests (28)**: Multi-tenant, rollback, API functionality  
- **E2E tests (4)**: Full dashboard workflows

## Key Features Verified

✅ **Run → Rollback → Run again** flow works end-to-end  
✅ **Tenant isolation**: A cannot see/rollback B's runs  
✅ **Concurrent run protection**: 409 error for overlapping runs  
✅ **Idempotent rollback**: Safe to call multiple times  
✅ **Golden parity**: Maintains exact calculation accuracy  
✅ **File uploads**: CSV validation and processing  
✅ **Journal entries**: Export for Xero/QuickBooks  

## Monitoring

### Health Checks
- API: `GET /health`
- Database: Monitor Supabase dashboard
- Frontend: Vercel deployment status

### Logging
- API logs: Available in Render/Fly dashboards
- Frontend: Browser console and Vercel function logs  
- Database: Supabase logs and metrics

## Support

### Common Issues

1. **CORS errors**: Ensure API URL is correctly set in frontend env vars
2. **Auth issues**: Check Supabase keys and RLS policies
3. **Upload failures**: Verify file format matches templates
4. **Rollback failures**: Ensure run exists and is in correct state

### Debug Commands

```bash
# Test CLI locally
python -m app.cli run --tenant-id debug --sales-file golden/golden_sales_clean.csv --dry-run

# Check API health
curl http://localhost:8000/health

# Test file upload
curl -X POST http://localhost:8000/api/v1/files/templates/sales
```

This system is production-ready with full audit trails, multi-tenant isolation, and comprehensive rollback support!