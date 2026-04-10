import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 1. Setup ---
# Credentials pulled from GitHub Secrets for security
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Farm location: Agadir region, Morocco
FARM_LAT = 30.42 
FARM_LON = -9.60
FARM_NAME = "Test Farm - Souss-Massa"

def run_agent():
    # --- 2. Fetch NASA Historical Data ---
    if not URL or not KEY:
        print(" Error: SUPABASE_URL or SUPABASE_KEY is missing from environment secrets!")
        return
    print(f"Agent starting: Connecting to {URL}...")
    
    today = datetime.now()
    start = (today - timedelta(days=3)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    
    nasa_url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,RH2M&community=AG&longitude={FARM_LON}&latitude={FARM_LAT}&start={start}&end={end}&format=JSON"
    nasa_res = requests.get(nasa_url, timeout=30).json()
    
    # --- 3. Fetch Open-Meteo Forecast ---
    forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={FARM_LAT}&longitude={FARM_LON}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Africa/Casablanca"
    forecast_res = requests.get(forecast_url, timeout=30).json()

    # --- 4. Clean Data (-999.0 Handling) ---
    historical = nasa_res['properties']['parameter']
    for param in historical:
        for date in historical[param]:
            if historical[param][date] == -999.0:
                historical[param][date] = None

    # Prepare the structured JSON for the Coordinator Agent
    agent_output = {
        "agent": "weather_agent",
        "timestamp": datetime.now().isoformat(),
        "historical": historical,
        "forecast_7day": forecast_res.get('daily', {}),
        "alerts": []
    }

    # Simple logic for Souss-Massa water scarcity
    if sum(forecast_res['daily'].get('precipitation_sum', [0])) < 0.5:
        agent_output["alerts"].append({"type": "irrigation", "msg": "No rain expected: Check soil moisture."})

    # --- 5. Push to Supabase weather_logs table ---
    supabase.table("weather_logs").insert({
        "farm_name": FARM_NAME,
        "latitude": FARM_LAT,
        "longitude": FARM_LON,
        "weather_data": agent_output 
    }).execute()
    
    print(" Agent run successful. Data synced to Supabase.")

if __name__ == "__main__":
    run_agent()
