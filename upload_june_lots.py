#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import shutil

# Load environment variables from .env file
load_dotenv()

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://mdjukynmoingazraqyio.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kanVreW5tb2luZ2F6cmFxeWlvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcyNTY4MjIsImV4cCI6MjA2MjgzMjgyMn0.ebRyktrN2kKAsIsrWFI4eWP3YhrbCPTTt54F2CYp06o'

# Temporarily rename the June file to the expected name
shutil.copy('lots_to_upload_June_clean.csv', 'lots_to_upload.csv')

# Now run the lot uploader
exec(open('supabase_lot_uploader.py').read()) 