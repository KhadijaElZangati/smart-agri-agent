Weather agents :

Technical Implementation Journey
The development of the Smart-Agri Weather Agent followed a five-stage engineering process designed for high availability and security.

Phase 1: Environment & Secrets Management
Infrastructure: Configured a local development environment on Ubuntu (Linux) using a Python 3.12 virtual environment (myenv).

Secrets Management: Implemented a non-repo-tracked .env system to handle sensitive credentials (API Keys and Database URLs).

Supabase Integration: Established a cloud-based PostgreSQL backend using Supabase to persist weather data for long-term agricultural analytics and multi-agent access.

Phase 2: Online Intelligence (Cloud Forecasting)
API Integration: Developed the online_weather_agent.py to interface with Open-Meteo and NASA POWER APIs, fetching hyper-local data for the Souss-Massa region.

Automation (GitHub Actions): Designed a .github/workflows/daily_weather.yml CI/CD pipeline. This automates daily data synchronization, using GitHub Secrets to securely inject Supabase credentials into the cloud runner.

Phase 3: Offline Intelligence (Edge-AI Vision)
Backbone Selection: Chose the NVIDIA MiT-B0 (Mix Transformer) for its efficiency on resource-constrained hardware (CPU-only inference).

Dataset Preparation: Managed a dataset of 3,400+ images across 11 weather classes (Dew, Sandstorm, Fog/Smog, etc.).

Edge Training: Performed 10-epoch training locally on a ThinkPad T450 (i5 CPU), achieving a final training loss of 0.0456.

Vision Perception: Verified the model’s ability to perform "now-casting" with a 99.2% confidence rate for local atmospheric conditions.

Phase 4: System Refactoring & Modularity
Separation of Concerns: Transitioned from a flat-file structure to a modular directory architecture:

<img width="1368" height="768" alt="Gemini_Generated_Image_lxg87dlxg87dlxg8" src="https://github.com/user-attachments/assets/397c9dd1-5994-408f-9874-3fce9ad98101" />



agents/: All operational logic (Online/Offline).

models/: Binary weights (.pth) and serialized brains.

coordinator/: Intelligent state management.

config/: Local state files (.json).

Path Resilience: Updated all Python scripts with os.path logic to ensure location-independent execution across different hardware environments.

Phase 5: The Fail-Safe Coordinator
Connectivity Gate: Developed the coordinator_agent.py to act as a system manager.

Dynamic Toggling: Implemented a heartbeat check that detects internet outages and automatically switches the "Source of Truth" from the Cloud API to the Local MiT-B0 Vision Agent.
