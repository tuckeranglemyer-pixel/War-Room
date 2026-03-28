"""
Configuration constants for The War Room.
Centralized settings for models, API endpoints, and feature flags.
"""

# Model Configuration
LOCAL_MODEL = "ollama/llama3.1:8b"
LOCAL_BASE_URL = "http://localhost:11434"

# DGX Spark model assignments (uncomment during DGX window)
# FIRST_TIMER_MODEL = "ollama/llama3.3:70b"
# DAILY_DRIVER_MODEL = "ollama/qwen3:32b"
# BUYER_MODEL = "ollama/mistral-small:24b"

# RAG Configuration
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "pm_tools"
RAG_RESULTS_PER_QUERY = 5

# Swarm Configuration
MAX_SCOUTS = 20
MAX_WORKERS = 10

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
