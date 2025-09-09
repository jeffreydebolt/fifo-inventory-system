#!/bin/bash

echo "Checking production API status..."
echo "================================"

echo -e "\n1. Health check:"
curl -s https://api.firstlot.co/health | python3 -m json.tool

echo -e "\n\n2. Database debug endpoint:"
curl -s https://api.firstlot.co/debug/database | python3 -m json.tool

echo -e "\n\n3. Testing file upload endpoint:"
curl -s -X POST https://api.firstlot.co/api/v1/files/upload \
  -H "Content-Type: multipart/form-data" \
  | python3 -m json.tool

echo -e "\n\nDone!"