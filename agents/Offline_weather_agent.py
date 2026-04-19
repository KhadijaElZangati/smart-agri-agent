import os
import json
import torch
from PIL import Image
from datetime import datetime
from torchvision import transforms
# We now import the Config class specifically
from transformers import SegformerConfig, SegformerForImageClassification

# --- 1. DYNAMIC PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Localized paths
CONFIG_PATH = os.path.join(BASE_DIR, "..", "models", "mit-b0-config")
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "weatherModel.pth")
IMAGE_FEED_DIR = os.path.join(BASE_DIR, "..", "local_camera_feed")
LOCAL_WEATHER_JSON = os.path.join(BASE_DIR, "..", "config", "local_weather_state.json")

WEATHER_CLASSES = [
    "dew", "fogsmog", "frost", "glaze", "hail", 
    "lightning", "rain", "rainbow", "rime", "sandstorm", "snow"
]

# --- 2. LOAD THE BRAIN (The Zero-Internet Method) ---
print(f"[{datetime.now().strftime('%H:%M:%S')}] Building MiT-B0 architecture from local blueprints...")

# 1. Load the Blueprints (config.json)
try:
    config = SegformerConfig.from_pretrained(CONFIG_PATH, local_files_only=True)
    # Ensure the label count matches your training
    config.num_labels = 11 
except Exception as e:
    raise OSError(f"❌ CRITICAL: Could not load config from {CONFIG_PATH}. Run the config-save command first! Error: {e}")

# 2. Build the Model Shell (The Body)
# This creates the architecture in memory WITHOUT looking for weights files
model = SegformerForImageClassification(config)

# 3. Load your Custom Weights (The Brain)
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"❌ ERROR: Trained weights (.pth) not found at {MODEL_PATH}!")

try:
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    print("  Success: Model loaded fully offline using custom weights.")
except Exception as e:
    print(f" ❌ ERROR: Failed to load weights into architecture: {e}")
    exit(1)

# Research-standard pre-processing
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.48, 0.47, 0.42], std=[0.226, 0.225, 0.227])
])

def run_real_inference(image_path):
    """Performs real vision classification on the edge"""
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
        print("⚠️ No input images found in feed.")
        return

    # Process latest 'capture' based on modification time
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

    # Ensure config directory exists
    os.makedirs(os.path.dirname(LOCAL_WEATHER_JSON), exist_ok=True)

    with open(LOCAL_WEATHER_JSON, 'w') as f:
        json.dump(weather_state, f, indent=2)
    
    print(f"  Real Perception: Detected {condition.upper()} ({conf*100:.1f}%)")

if __name__ == "__main__":
    run_agent()
