import os
import json
import torch
from PIL import Image
from datetime import datetime
from torchvision import transforms
from transformers import SegformerForImageClassification

# --- 1. DYNAMIC PATH CONFIGURATION ---
# Points to the 'agents/' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Localized paths for total autonomy
CONFIG_PATH = os.path.join(BASE_DIR, "..", "models", "mit-b0-config")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "weatherModel.pth")
IMAGE_FEED_DIR = os.path.join(BASE_DIR, "..", "local_camera_feed")
LOCAL_WEATHER_JSON = os.path.join(BASE_DIR, "..", "config", "local_weather_state.json")

WEATHER_CLASSES = [
    "dew", "fogsmog", "frost", "glaze", "hail", 
    "lightning", "rain", "rainbow", "rime", "sandstorm", "snow"
]

# --- 2. LOAD THE BRAIN (Zero-Internet Mode) ---
print(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing MiT-B0 from local config...")

# Safety check for the config folder
if not os.path.exists(CONFIG_PATH):
    raise OSError(f"❌ CRITICAL: Configuration folder missing at {CONFIG_PATH}. Run the config-save command first!")

# Load the architecture using the local folder ONLY
model = SegformerForImageClassification.from_pretrained(
    CONFIG_PATH, 
    local_files_only=True, 
    num_labels=11, 
    ignore_mismatched_sizes=True
)

# Load the custom weights (.pth file)
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"❌ ERROR: Trained weights not found at {MODEL_PATH}!")

model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
model.eval()

# Research-standard pre-processing
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.48, 0.47, 0.42], std=[0.226, 0.225, 0.227])
])

def run_real_inference(image_path):
    img = Image.open(image_path).convert("RGB")
    input_tensor = transform(img).unsqueeze(0) 
    
    with torch.no_grad():
        outputs = model(pixel_values=input_tensor)
        logits = outputs.logits
        predicted_idx = torch.argmax(logits, dim=1).item()
        confidence = torch.softmax(logits, dim=1)[0][predicted_idx].item()
        
    return WEATHER_CLASSES[predicted_idx], confidence

def run_agent():
    if not os.path.exists(IMAGE_FEED_DIR):
        print(f"❌ ERROR: Camera feed directory {IMAGE_FEED_DIR} missing.")
        return

    print(f"🔍 Offline Agent monitoring feed...")
    
    files = [os.path.join(IMAGE_FEED_DIR, f) for f in os.listdir(IMAGE_FEED_DIR) 
             if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not files:
        print(" No input images found.")
        return

    # Process latest 'capture'
    latest_img = max(files, key=os.path.getmtime)
    condition, conf = run_real_inference(latest_img)

    weather_state = {
        "agent": "weather_agent_offline",
        "timestamp": datetime.now().isoformat(),
        "perceived_condition": condition,
        "confidence": round(conf, 4),
        "source": "Local MiT-B0 Vision",
        "is_offline_mode": True
    }

    os.makedirs(os.path.dirname(LOCAL_WEATHER_JSON), exist_ok=True)
    with open(LOCAL_WEATHER_JSON, 'w') as f:
        json.dump(weather_state, f, indent=2)
    
    print(f"  Real Perception: Detected {condition.upper()} ({conf*100:.1f}%)")

if __name__ == "__main__":
    run_agent()
