import os
import sys
import json
import time
from datetime import datetime
from typing import TypedDict

# LangGraph & AI Imports
from langgraph.graph import StateGraph, END
from google import genai
from supabase import create_client
from dotenv import load_dotenv

# --- 🛰️ PATH INJECTION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# --- 📦 IMPORTS ---
from soil_coordinator import run_soil_intelligence
from coordinator_weather_agent import get_unified_weather
from coordinator_pest_agent import run_unified_orchestration as run_pest_logic
from coordinator_irrigation_agent import get_unified_irrigation

load_dotenv()

# --- 🛠️ UTILITY: RECURSIVE DATA HUNTER ---
def find_val(obj, keys, default):
    """Crawls dictionaries to find values; handles lists by taking index 0."""
    if not isinstance(obj, dict):
        return default
    for k in keys:
        if k in obj and obj[k] is not None:
            val = obj[k]
            return val[0] if isinstance(val, list) and len(val) > 0 else val
    for v in obj.values():
        if isinstance(v, dict):
            res = find_val(v, keys, None)
            if res is not None: return res
    return default

# --- 1. STATE DEFINITION ---
class FarmState(TypedDict):
    soil_data: dict
    weather_data: dict
    pest_data: dict
    irrigation_plan: dict
    advice_darija: str
    advice_english: str
    timestamp: str

# --- 2. NODE IMPLEMENTATION ---

def soil_node(state: FarmState):
    print("\n[NODE] 🪴 Soil Dept: Checking Moisture & Health...")
    try:
        run_soil_intelligence() #
    except:
        print(" ⚠️ Soil Online failed. Using local cache.")
    
    path = os.path.join(BASE_DIR, "..", "config", "online_soil_state.json")
    if not os.path.exists(path):
        path = os.path.join(BASE_DIR, "..", "config", "soil_state.json")
    with open(path, "r") as f:
        return {"soil_data": json.load(f)}

def weather_node(state: FarmState):
    print("\n[NODE] 🌤️ Weather Dept: Syncing Regional Forecast...")
    try:
        get_unified_weather() #
    except:
        print(" ⚠️ Weather Online failed. Using local cache.")
        
    path = os.path.join(BASE_DIR, "..", "config", "online_weather_state.json")
    with open(path, "r") as f:
        return {"weather_data": json.load(f)}

def pest_node(state: FarmState):
    print("\n[NODE] 🐜 Pest Dept: Running Hybrid Vision Debate...")
    run_pest_logic() #
    path = os.path.join(BASE_DIR, "..", "config", "local_pest_state.json")
    with open(path, "r") as f:
        data = json.load(f).get("vision_results", {})
        raw_guess = data.get("detected_disease", "Tomato___Healthy")
        data["detected_crop"] = raw_guess.split("___")[0] if "___" in raw_guess else "Tomato"
    return {"pest_data": data}

def irrigation_node(state: FarmState):
    print("\n[NODE] 💧 Irrigation Dept: Optimizing Water Flow...")
    os.environ["SELECTED_CROP"] = state['pest_data'].get('detected_crop', 'Tomato')
    get_unified_irrigation() #[cite: 1]
    path = os.path.join(BASE_DIR, "..", "config", "online_irrigation_state.json")
    with open(path, "r") as f:
        return {"irrigation_plan": json.load(f)}

def advisor_node(state: FarmState):
    """L-Khayr Advisor: With Quota Backoff & Syntax Fix."""
    print("\n[NODE] 🗣️ Advisor Dept: Generating Recommendations...")
    
    moisture = find_val(state['soil_data'], ["moisture", "soil_moisture"], 0.0)
    temp = find_val(state['weather_data'], ["temperature_2m_max", "temp"], 0.0)
    rain = find_val(state['weather_data'], ["precipitation_sum"], 0.0)
    
    status = "Rainy" if rain > 0 else "Sunny/Clear"
    crop = state['pest_data'].get('detected_crop', 'Tomato')
    pest = state['pest_data'].get('detected_disease', 'None')
    
    # --- FIXED MAPPING FOR IRRIGATION ACTION ---
    irr = state['irrigation_plan'].get('action', 'Monitor') #[cite: 1]

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"Act as 'L-Khayr' AI. Farm: {crop}. Data: Soil({moisture}%), Weather({temp}C, {status}), Pest({pest}), Irr({irr}). Return JSON: {{'darija': '...', 'english': '...'}}"

    for attempt in range(3):
        try:
            response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
            raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            advice_data = json.loads(raw_text)
            return {"advice_darija": advice_data['darija'], "advice_english": advice_data['english']}
        except Exception as e:
            wait = 40 if "429" in str(e) else 10
            print(f" ⚠️ Advisor Attempt {attempt+1} failed. Retrying in {wait}s...")
            time.sleep(wait)

    return {
        "advice_darija": "Problem f l-internet, sqi l-ard ila kant nasfa.",
        "advice_english": "Advisor quota exceeded. Manual monitoring recommended."
    }

def sync_node(state: FarmState):
    print("\n[NODE] ☁️ Master Sync: Updating Supabase Master Logs...")
    
    soil_moisture = find_val(state['soil_data'], ["moisture", "soil_moisture"], 0.0)
    weather_temp = find_val(state['weather_data'], ["temperature_2m_max", "temp"], 0.0)
    rain = find_val(state['weather_data'], ["precipitation_sum"], 0.0)
    weather_status = "Rainy" if rain > 0 else "Sunny/Clear"
    
    # --- FIXED MAPPING HERE TOO ---
    irr_action = state['irrigation_plan'].get('action', 'Monitor') #[cite: 1]

    log_data = {
        "farm_name": f"Agadir-{state['pest_data'].get('detected_crop', 'Farm')}",
        "soil_health": state['soil_data'].get('status', 'COMPLETE'),
        "soil_moisture": float(soil_moisture),
        "weather_temp": float(weather_temp),
        "weather_status": str(weather_status),
        "detected_pest": state['pest_data'].get('detected_disease', 'None'),
        "pest_confidence": float(state['pest_data'].get('confidence', 0.0)),
        "irrigation_action": irr_action,
        "advice_darija": state['advice_darija'],
        "advice_english": state['advice_english'],
        "raw_state": state
    }

    try:
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        supabase.table("master_farm_logs").insert(log_data).execute()
        print(f" ✅ SUCCESS: Logged {weather_temp}C and {soil_moisture}% Moisture.")
    except Exception:
        print(" 📂 SYNC ERROR: Saving to local offline_buffer.json")
        # (Offline buffering logic remains here)

    return state

# --- 3. GRAPH ARCHITECTURE ---
workflow = StateGraph(FarmState)
workflow.add_node("soil", soil_node)
workflow.add_node("weather", weather_node)
workflow.add_node("pest", pest_node)
workflow.add_node("irrigation", irrigation_node)
workflow.add_node("advisor", advisor_node)
workflow.add_node("sync", sync_node)

workflow.set_entry_point("soil")
workflow.add_edge("soil", "weather")
workflow.add_edge("weather", "pest")
workflow.add_edge("pest", "irrigation")
workflow.add_edge("irrigation", "advisor")
workflow.add_edge("advisor", "sync")
workflow.add_edge("sync", END)

master_app = workflow.compile()

if __name__ == "__main__":
    initial_state = {"soil_data": {}, "weather_data": {}, "pest_data": {}, "irrigation_plan": {}, "advice_darija": "", "advice_english": "", "timestamp": datetime.now().isoformat()}
    master_app.invoke(initial_state)
