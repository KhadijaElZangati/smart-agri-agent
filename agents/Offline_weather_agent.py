import os
import json
import torch
from PIL import Image
from datetime import datetime
from torchvision import transforms
from transformers import SegformerForImageClassification

# --- 1. CONFIGURATION ---
IMAGE_FEED_DIR = "./local_camera_feed"
LOCAL_WEATHER_JSON = "local_weather_state.json"
MODEL_PATH = "weatherModel.pth"

# 11 Classes as defined in the research paper [cite: 1, 232]
WEATHER_CLASSES = [
    "dew", "fogsmog", "frost", "glaze", "hail", 
    "lightning", "rain", "rainbow", "rime", "sandstorm", "snow"
]

# --- 2. LOAD THE BRAIN ---
print("Loading trained MiT-B0 model...")
# Initialize the architecture [cite: 1, 62, 218]
model = SegformerForImageClassification.from_pretrained(
    "nvidia/mit-b0", 
    num_labels=11, 
    ignore_mismatched_sizes=True
)
# Load your specific weights 
model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
model.eval()

# Research-standard pre-processing [cite: 1, 225]
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.48, 0.47, 0.42], std=[0.226, 0.225, 0.227])
])

def run_real_inference(image_path):
    """
    Performs real vision classification on the edge [cite: 1, 188]
    """
    img = Image.open(image_path).convert("RGB")
    input_tensor = transform(img).unsqueeze(0) # Add batch dimension
    
    with torch.no_grad():
        outputs = model(pixel_values=input_tensor)
        logits = outputs.logits
        predicted_idx = torch.argmax(logits, dim=1).item()
        confidence = torch.softmax(logits, dim=1)[0][predicted_idx].item()
        
    return WEATHER_CLASSES[predicted_idx], confidence

def run_agent():
    print(f"[{datetime.now()}] Offline Agent active. Monitoring {IMAGE_FEED_DIR}...")
    
    files = [os.path.join(IMAGE_FEED_DIR, f) for f in os.listdir(IMAGE_FEED_DIR) 
             if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not files:
        return

    # Process the latest 'capture'
    latest_img = max(files, key=os.path.getmtime)
    condition, conf = run_real_inference(latest_img)

    # Prepare the fail-safe JSON for the Coordinator [cite: 1, 206]
    weather_state = {
        "agent": "weather_agent_offline",
        "timestamp": datetime.now().isoformat(),
        "perceived_condition": condition,
        "confidence": round(conf, 4),
        "source": "Local MiT-B0 Vision",
        "is_offline_mode": True
    }

    with open(LOCAL_WEATHER_JSON, 'w') as f:
        json.dump(weather_state, f, indent=2)
    
    print(f" Real Perception: Detected {condition.upper()} ({conf*100:.1f}%)")

if __name__ == "__main__":
    run_agent()
