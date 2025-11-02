# api/supabase_client.py
from supabase import create_client

url = "https://jxpkukugslcgttigovpl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp4cGt1a3Vnc2xjZ3R0aWdvdnBsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEyOTM0NDIsImV4cCI6MjA3Njg2OTQ0Mn0.S0W3SSXqMbHF0loIeYwifUQKbl-bgXtp_dapk2FM67g"
supabase = create_client(url, key)
