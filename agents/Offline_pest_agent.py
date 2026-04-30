import os
import json
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "pest_model.pth")
CLASSES_PATH = os.path.join(BASE_DIR, "..", "config", "class_names.json")
CAMERA_DIR = os.path.join(BASE_DIR, "..", "local_camera_feed")
PEST_STATE = os.path.join(BASE_DIR, "..", "config", "local_pest_state.json")
TRUST_THRESHOLD = 0.50 #

def get_class_names():
    if os.path.exists(CLASSES_PATH):
        with open(CLASSES_PATH, 'r') as f:
            return json.load(f)
    return ["Unknown"]

CLASS_NAMES = get_class_names()

def load_trained_model():
    model = models.mobilenet_v2(weights=None)
    # Match the 15 classes from your training session
    model.classifier[1] = nn.Linear(model.last_channel, len(CLASS_NAMES))
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device('cpu')))
        print(f"  ✅ Weights loaded for {len(CLASS_NAMES)} classes.")
    model.eval()
    return model

preprocess = transforms.Compose([
    transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def run_real_inference():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Offline Pest Agent: Running CNN Inference...")
    images = [f for f in os.listdir(CAMERA_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if not images: 
        print("  ⚠️ No image found.")
        return

    latest_img_path = os.path.join(CAMERA_DIR, images[-1])
    img = Image.open(latest_img_path)
    img_t = preprocess(img)
    batch_t = torch.unsqueeze(img_t, 0)

    model = load_trained_model()
    with torch.no_grad():
        out = model(batch_t)
    
    percentage = torch.nn.functional.softmax(out, dim=1)[0] * 100
    confidence = torch.max(percentage).item() / 100
    result = CLASS_NAMES[torch.argmax(percentage).item()]

    # Decision logic based on confidence
    final_label = result if confidence >= TRUST_THRESHOLD else "Low_Confidence_Unknown"
    
    output = {
        "agent": "pest_agent_offline",
        "timestamp": datetime.now().isoformat(),
        "vision_results": {
            "detected_disease": final_label,
            "raw_guess": result,
            "confidence": round(confidence, 2),
            "is_trusted": confidence >= TRUST_THRESHOLD
        },
        "is_offline_mode": True
    }

    with open(PEST_STATE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"   Result: {final_label} ({round(confidence*100, 2)}%)")

if __name__ == "__main__":
    run_real_inference()
