# Render Environment Variable Setup

To fix the Supabase database connection in production, you need to set these environment variables in your Render dashboard:

## Required Environment Variables

1. **SUPABASE_URL**: `https://mdjukynmoingazraqyio.supabase.co`
2. **SUPABASE_ANON_KEY**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kanVreW5tb2luZ2F6cmFxeWlvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcyNTY4MjIsImV4cCI6MjA2MjgzMjgyMn0.ebRyktrN2kKAsIsrWFI4eWP3YhrbCPTTt54F2CYp06o`

## Steps to Add Environment Variables on Render:

1. Go to your Render dashboard
2. Select your service (api.firstlot.co)
3. Go to the "Environment" tab
4. Add the following environment variables:
   - Click "Add Environment Variable"
   - Add SUPABASE_URL with the value above
   - Add SUPABASE_ANON_KEY with the value above
5. Save changes
6. Render will automatically redeploy your service

## Verify the Connection

After deployment, visit: https://api.firstlot.co/debug/database

This endpoint will show:
- Whether environment variables are detected
- Whether the Supabase client initialized
- The result of a test database query

The response should look like:
```json
{
  "timestamp": "...",
  "environment_variables": {
    "SUPABASE_URL_exists": true,
    "SUPABASE_URL_length": 44,
    "SUPABASE_ANON_KEY_exists": true,
    "SUPABASE_ANON_KEY_length": 253
  },
  "supabase_client_status": true,
  "database_test": {
    "status": "success",
    "rows_returned": 1,
    "error": null
  }
}
```