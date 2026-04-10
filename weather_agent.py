import os
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 1. Setup from GitHub Secrets ---
# These must match your GitHub Secret names exactly
# --- 1. Configuration & Secrets ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# --- 2. Dynamic Inputs with Souss-Massa Defaults ---
# This looks for 'FARM_LAT' in GitHub, otherwise uses Agadir cordinates
LAT = float(os.environ.get("FARM_LAT", 30.42)) 
LON = float(os.environ.get("FARM_LON", -9.60))
NAME = os.environ.get("FARM_NAME", "Default Farm - Souss-Massa")

def run_agent():
    print(f"Agent starting for {NAME} at ({LAT}, {LON})...")
    # ... the rest of your logic stays the same, just use LAT and LON ...
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(" Error: SUPABASE_URL or SUPABASE_KEY is missing from environment secrets!")
        return

    print(f"Agent starting: Connecting to {SUPABASE_URL}...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 2. NASA Historical Data (Cleaning -999.0 values)
    today = datetime.now()
    start = (today - timedelta(days=3)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    nasa_url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,RH2M&community=AG&longitude={FARM_LON}&latitude={FARM_LAT}&start={start}&end={end}&format=JSON"
    nasa_res = requests.get(nasa_url).json()
    
    # Clean the -999.0 sensor errors
    params = nasa_res['properties']['parameter']
    for p in params:
        for d in params[p]:
            if params[p][d] == -999.0: 
                params[p][d] = None

    # 3. Open-Meteo 7-Day Forecast
    forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={FARM_LAT}&longitude={FARM_LON}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Africa/Casablanca"
    forecast_res = requests.get(forecast_url).json()

    # 4. Prepare JSON Output for Coordinator Agent
    agent_output = {
        "timestamp": datetime.now().isoformat(),
        "historical": params,
        "forecast": forecast_res.get('daily', {}),
        "alerts": []
    }

    # Custom alert for water scarcity in Souss-Massa 
    if sum(forecast_res['daily'].get('precipitation_sum', [0])) < 0.2:
        agent_output["alerts"].append("Critical: No rain forecast. Adjust irrigation.")

    # 5. Insert into Supabase weather_logs table
    data = {
        "farm_name": "Test Farm - Souss-Massa",
        "latitude": FARM_LAT,
        "longitude": FARM_LON,
        "weather_data": agent_output 
    }
    
    supabase.table("weather_logs").insert(data).execute()
    print(" Success! Data pushed to Supabase.")

if __name__ == "__main__":
    run_agent()
