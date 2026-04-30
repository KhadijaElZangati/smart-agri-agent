import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
# Correct way to get the variable from your .env file
EPPO_TOKEN = os.getenv("EPPO_TOKEN")
BASE_URL = "https://api.eppo.int/gd/v2" 
STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "online_pest_state.json")

def get_real_eppo_data(host_code="SOLYLY"): # Tomato (Solanum lycopersicum)
    print(f" [EPPO] Querying v2 API for {host_code} risks...")
    
    # Endpoint for pests associated with the host
    url = f"{BASE_URL}/taxon/{host_code}/pests"
    headers = {"X-Api-Key": EPPO_TOKEN}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            all_pests = response.json()
            # Filter top 5 scientific names for the GenAI Orchestrator
            risks = [p.get("scientificname") for p in all_pests[:5]]
            
            return {
                "source": "EPPO v2 Real-Time API",
                "active_alerts": risks,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"error": "API_ERROR", "status": response.status_code}
    except Exception as e:
        return {"error": str(e)}

def run_agent():
    if not EPPO_TOKEN:
        print(" ❌ Error: EPPO_TOKEN still missing in .env!")
        return
    
    data = get_real_eppo_data()
    with open(STATE_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print("  Online Agent: Real EPPO data synced.")

if __name__ == "__main__":
    run_agent()
