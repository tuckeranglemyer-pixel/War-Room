"""
Model and runtime configuration for War Room.

All model identifiers, endpoint URLs, and tunable knobs live here.
Swap between local dev (small Ollama models) and DGX Spark production
(Llama 70B / Qwen 32B / Mistral 24B) by editing the constants below or
setting the corresponding env vars before launching the server.
"""

# ---------------------------------------------------------------------------
# Local dev defaults (small models, single Ollama instance)
# ---------------------------------------------------------------------------

LOCAL_MODEL = "ollama/llama3.1:8b"
LOCAL_BASE_URL = "http://localhost:11434"
# Daily Driver and Buyer share this model in dev; First-Timer uses LOCAL_MODEL.
DAILY_DRIVER_BUYER_MODEL = "ollama/llama3.3:60b"

# ---------------------------------------------------------------------------
# DGX Spark production model assignments
# Each model serves on its own vLLM endpoint (ports 8001 / 8002 / 8003).
# Uncomment and set env vars when running the full adversarial debate stack.
# ---------------------------------------------------------------------------
# FIRST_TIMER_MODEL  = "ollama/llama3.3:70b"   # port 8001
# DAILY_DRIVER_MODEL = "ollama/qwen3:32b"       # port 8002
# BUYER_MODEL        = "ollama/mistral-small:24b" # port 8003

# ---------------------------------------------------------------------------
# RAG / ChromaDB
# ---------------------------------------------------------------------------

CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "pm_tools"
RAG_RESULTS_PER_QUERY = 5

# ---------------------------------------------------------------------------
# Swarm reconnaissance
# ---------------------------------------------------------------------------

MAX_SCOUTS = 20
MAX_WORKERS = 10

# ---------------------------------------------------------------------------
# API server
# ---------------------------------------------------------------------------

API_HOST = "0.0.0.0"
API_PORT = 8000
