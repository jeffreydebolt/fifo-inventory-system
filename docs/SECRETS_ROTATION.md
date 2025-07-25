# Secrets & Keys Rotation Guide

## Overview

This guide covers all secrets, API keys, and credentials used in the FIFO COGS system, where they are stored, and how to rotate them safely.

## Complete Secrets Inventory

### 1. Supabase Credentials

**SUPABASE_URL**
- **What**: Your Supabase project URL
- **Format**: `https://your-project-id.supabase.co`
- **Where stored**:
  - API: `SUPABASE_URL` environment variable
  - Dashboard: `REACT_APP_SUPABASE_URL` environment variable
  - CI/CD: Repository secrets
- **Rotation frequency**: Only when migrating to new Supabase project
- **Impact**: High - entire system becomes unavailable

**SUPABASE_ANON_KEY**
- **What**: Public anonymous key for client-side operations
- **Format**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- **Where stored**:
  - Dashboard: `REACT_APP_SUPABASE_ANON_KEY` environment variable
  - CI/CD: Repository secrets (for builds)
- **Rotation frequency**: Every 90 days or when compromised
- **Impact**: Medium - dashboard stops working until updated

**SUPABASE_SERVICE_ROLE_KEY**
- **What**: Service role key for server-side operations (bypasses RLS)
- **Format**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- **Where stored**:
  - API: `SUPABASE_SERVICE_ROLE_KEY` environment variable
  - CI/CD: Repository secrets
- **Rotation frequency**: Every 30 days
- **Impact**: High - API cannot perform database operations

### 2. Deployment Credentials

**DOCKER_USERNAME & DOCKER_PASSWORD**
- **What**: Docker Hub credentials for image publishing
- **Where stored**: GitHub repository secrets
- **Rotation frequency**: Every 90 days
- **Impact**: Medium - cannot deploy new API versions

**RENDER_API_KEY & RENDER_SERVICE_ID**
- **What**: Render.com deployment credentials
- **Where stored**: GitHub repository secrets
- **Rotation frequency**: Every 90 days
- **Impact**: Medium - cannot auto-deploy API

**VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID**
- **What**: Vercel deployment credentials
- **Where stored**: GitHub repository secrets
- **Rotation frequency**: Every 90 days
- **Impact**: Medium - cannot auto-deploy dashboard

**FLY_API_TOKEN** (if using Fly.io)
- **What**: Fly.io deployment token
- **Where stored**: GitHub repository secrets
- **Rotation frequency**: Every 90 days
- **Impact**: Medium - cannot deploy to Fly.io

### 3. Monitoring & Error Tracking

**SENTRY_DSN**
- **What**: Sentry Data Source Name for error tracking
- **Format**: `https://key@organization.ingest.sentry.io/project`
- **Where stored**:
  - API: `SENTRY_DSN` environment variable
  - Dashboard: `REACT_APP_SENTRY_DSN` environment variable
- **Rotation frequency**: Only when regenerating project keys
- **Impact**: Low - error tracking stops, but system continues working

### 4. Application Secrets

**JWT_SECRET** or similar (if implemented)
- **What**: Secret for signing JWT tokens
- **Where stored**: API environment variables
- **Rotation frequency**: Every 30 days
- **Impact**: High - all user sessions invalidated

## Rotation Procedures

### Rotating Supabase Service Role Key

**⚠️ HIGH IMPACT - Plan for maintenance window**

1. **Generate new service role key**:
   ```bash
   # In Supabase Dashboard
   # Go to Settings → API
   # Click "Generate new service role key"
   # Copy the new key
   ```

2. **Update in deployment platforms**:
   ```bash
   # Render.com
   curl -X PATCH "https://api.render.com/v1/services/$RENDER_SERVICE_ID/env-vars" \
     -H "Authorization: Bearer $RENDER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "SUPABASE_SERVICE_ROLE_KEY": "new_service_role_key_here"
     }'
   
   # Fly.io
   fly secrets set SUPABASE_SERVICE_ROLE_KEY="new_service_role_key_here"
   ```

3. **Update CI/CD secrets**:
   ```bash
   # GitHub CLI
   gh secret set SUPABASE_SERVICE_ROLE_KEY --body "new_service_role_key_here"
   ```

4. **Test the rotation**:
   ```bash
   # Health check
   curl https://your-api-url.com/health
   
   # Test database operation
   curl -X GET "https://your-api-url.com/api/v1/runs?tenant_id=test-tenant"
   ```

5. **Revoke old key**:
   ```bash
   # In Supabase Dashboard
   # Go to Settings → API
   # Find old service role key and click "Revoke"
   ```

### Rotating Supabase Anon Key

**Medium impact - Dashboard will be affected**

1. **Generate new anon key**:
   - Supabase Dashboard → Settings → API
   - Click "Generate new anon key"

2. **Update dashboard deployment**:
   ```bash
   # Vercel
   vercel env add REACT_APP_SUPABASE_ANON_KEY production
   # Enter the new key when prompted
   
   # Trigger redeploy
   vercel --prod
   ```

3. **Update CI/CD secrets**:
   ```bash
   gh secret set REACT_APP_SUPABASE_ANON_KEY --body "new_anon_key_here"
   ```

4. **Test dashboard functionality**:
   - Visit dashboard URL
   - Test login/logout
   - Test file upload
   - Test run creation

5. **Revoke old key** (in Supabase Dashboard)

### Emergency Key Rotation Script

Create this script for quick emergency rotation:

```bash
#!/bin/bash
# emergency_key_rotation.sh

set -e

echo "🚨 EMERGENCY KEY ROTATION SCRIPT"
echo "This will rotate the Supabase service role key immediately"
read -p "Are you sure? (type 'YES' to continue): " confirm

if [ "$confirm" != "YES" ]; then
    echo "Aborted"
    exit 1
fi

echo "📝 Step 1: Generate new service role key in Supabase Dashboard"
echo "Go to: https://app.supabase.com/project/$SUPABASE_PROJECT_ID/settings/api"
read -p "Enter the NEW service role key: " NEW_KEY

if [ -z "$NEW_KEY" ]; then
    echo "❌ No key provided. Aborted."
    exit 1
fi

echo "🔄 Step 2: Updating deployment platforms..."

# Update Render
if [ -n "$RENDER_API_KEY" ] && [ -n "$RENDER_SERVICE_ID" ]; then
    echo "Updating Render..."
    curl -X PATCH "https://api.render.com/v1/services/$RENDER_SERVICE_ID/env-vars" \
      -H "Authorization: Bearer $RENDER_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"SUPABASE_SERVICE_ROLE_KEY\": \"$NEW_KEY\"}"
fi

# Update Fly.io
if command -v fly &> /dev/null; then
    echo "Updating Fly.io..."
    fly secrets set SUPABASE_SERVICE_ROLE_KEY="$NEW_KEY"
fi

# Update GitHub secrets
if command -v gh &> /dev/null; then
    echo "Updating GitHub secrets..."
    echo "$NEW_KEY" | gh secret set SUPABASE_SERVICE_ROLE_KEY
fi

echo "⏳ Step 3: Waiting for deployments to restart (30 seconds)..."
sleep 30

echo "🧪 Step 4: Testing new key..."
API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://your-api-url.com/health)

if [ "$API_HEALTH" = "200" ]; then
    echo "✅ API health check passed"
else
    echo "❌ API health check failed (HTTP $API_HEALTH)"
    echo "Check deployment logs immediately!"
    exit 1
fi

echo "✅ Emergency rotation complete!"
echo "📋 Manual steps remaining:"
echo "  1. Revoke the old key in Supabase Dashboard"
echo "  2. Update local development environment"
echo "  3. Notify team of the rotation"
```

Make it executable:
```bash
chmod +x scripts/emergency_key_rotation.sh
```

## Rotation Schedule

### Automated Reminders

Set up calendar reminders:

```bash
# Add to crontab for weekly rotation check
0 9 * * MON /path/to/check_key_expiry.sh
```

### Key Expiry Checker

```bash
#!/bin/bash
# check_key_expiry.sh

# Check when keys were last rotated
LAST_ROTATION_FILE="/var/log/fifo/last_key_rotation"

if [ -f "$LAST_ROTATION_FILE" ]; then
    LAST_ROTATION=$(cat "$LAST_ROTATION_FILE")
    DAYS_SINCE=$(( ($(date +%s) - $(date -d "$LAST_ROTATION" +%s)) / 86400 ))
    
    if [ "$DAYS_SINCE" -gt 30 ]; then
        echo "⚠️  Service role key rotation overdue by $((DAYS_SINCE - 30)) days"
        echo "Last rotated: $LAST_ROTATION"
        echo "Action required: Rotate SUPABASE_SERVICE_ROLE_KEY"
        
        # Send alert to monitoring system
        curl -X POST "$SLACK_WEBHOOK_URL" \
          -H 'Content-type: application/json' \
          --data '{"text":"🔑 FIFO COGS: Service role key rotation overdue"}'
    fi
else
    echo "⚠️  No rotation history found. Please rotate keys and run: echo $(date +%Y-%m-%d) > $LAST_ROTATION_FILE"
fi
```

## Security Best Practices

### Key Management
1. **Never commit secrets to git**
2. **Use environment variables, not config files**
3. **Rotate on schedule, not just when compromised**
4. **Test rotations in staging first**
5. **Keep rotation history for audit purposes**

### Access Control
1. **Limit who can rotate production keys**
2. **Require two-person approval for service role key rotation**
3. **Log all key rotation activities**
4. **Review access logs monthly**

### Incident Response
1. **If any key is compromised, rotate immediately**
2. **If service role key is compromised, treat as security incident**
3. **Document all emergency rotations**
4. **Perform post-incident review**

## Environment Variables Reference

### Production API
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiI...
SENTRY_DSN=https://key@org.ingest.sentry.io/project
ENVIRONMENT=production
APP_VERSION=1.0.0
DEBUG=false
PORT=8000
```

### Production Dashboard
```bash
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiI...
REACT_APP_API_BASE_URL=https://your-api.render.com
REACT_APP_SENTRY_DSN=https://key@org.ingest.sentry.io/project
REACT_APP_VERSION=1.0.0
```

### GitHub Repository Secrets
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
REACT_APP_SUPABASE_URL
REACT_APP_SUPABASE_ANON_KEY
REACT_APP_API_BASE_URL
DOCKER_USERNAME
DOCKER_PASSWORD
RENDER_API_KEY
RENDER_SERVICE_ID
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

## Troubleshooting

### Common Issues After Rotation

**API returns 401/403 errors**
- Check service role key is correctly updated
- Verify key hasn't been revoked too early
- Test with curl commands

**Dashboard can't authenticate**
- Check anon key is correctly updated
- Clear browser cache/localStorage
- Verify Supabase URL matches

**CI/CD deploys fail**
- Check GitHub secrets are updated
- Verify secret names match exactly
- Re-run failed workflows

### Recovery from Failed Rotation

1. **Immediately revert to previous working key** (if not revoked)
2. **Check deployment logs for specific errors**
3. **Test each component individually**
4. **Contact Supabase support if keys are lost**

Remember: Keep old keys active until new keys are fully deployed and tested!