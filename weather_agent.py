import os
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- 1. Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# --- 2. Dynamic Inputs with Souss-Massa Defaults ---
# This allows our future Coordinator Agent to send different coordinates [cite: 107, 108]
FARM_LAT = float(os.environ.get("FARM_LAT", 30.42)) 
FARM_LON = float(os.environ.get("FARM_LON", -9.60))
FARM_NAME = os.environ.get("FARM_NAME", "Default Farm - Souss-Massa")

def run_agent():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(" Error: Supabase credentials missing!")
        return

    print(f"Agent starting for {FARM_NAME} at ({FARM_LAT}, {FARM_LON})...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 3. Fetch NASA Data
    today = datetime.now()
    start = (today - timedelta(days=3)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    
    # We use FARM_LON and FARM_LAT here to match the definitions above
    nasa_url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,RH2M&community=AG&longitude={FARM_LON}&latitude={FARM_LAT}&start={start}&end={end}&format=JSON"
    nasa_res = requests.get(nasa_url).json()
    
    # Clean -999.0 values
    params = nasa_res['properties']['parameter']
    for p in params:
        for d in params[p]:
            if params[p][d] == -999.0: params[p][d] = None

    # 4. Fetch Open-Meteo Forecast
    forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={FARM_LAT}&longitude={FARM_LON}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Africa/Casablanca"
    forecast_res = requests.get(forecast_url).json()

    # 5. Build Output
    agent_output = {
        "timestamp": datetime.now().isoformat(),
        "historical": params,
        "forecast": forecast_res.get('daily', {}),
        "alerts": []
    }

    # Souss-Massa specific water scarcity alert [cite: 94, 99]
    if sum(forecast_res['daily'].get('precipitation_sum', [0])) < 0.2:
        agent_output["alerts"].append("Critical: No rain forecast. Adjust irrigation.")

    # 6. Sync to Supabase
    supabase.table("weather_logs").insert({
        "farm_name": FARM_NAME,
        "latitude": FARM_LAT,
        "longitude": FARM_LON,
        "weather_data": agent_output 
    }).execute()
    
    print(" Success! Dynamic Weather Data Synced.")

if __name__ == "__main__":
    run_agent()
