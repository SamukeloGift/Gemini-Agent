import os
from dotenv import load_dotenv
load_dotenv()

class AgentConfig:
    """Configurations for the AI agent."""

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY not found!")
        print("Please create a .env file in your project root with:")
        print("GEMINI_API_KEY=your_api_key_here")
        print("Or set it as an environment variable.")

    _MODEL_CHOICE = os.getenv('GEMINI_MODEL', '2.5-flash').lower()
    MODEL_NAME = {
        '2.5-pro': 'models/gemini-2.5-pro-exp-03-25',
        '2.5-flash': 'models/gemini-2.5-flash-preview-05-20'
    }.get(_MODEL_CHOICE, 'models/gemini-2.5-flash-preview-05-20') # Default flash

    TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
    TOP_K = int(os.getenv('TOP_K', 40))
    TOP_P = float(os.getenv('TOP_P', 0.95))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', 2048))
    MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', 15)) # Reduce from 15 to a lower num for fast & less responses..

    # Set ENABLE_MEMORY=true in your environment to activate it.
    # switched off due to slownesss..
    ENABLE_MEMORY = os.getenv('ENABLE_MEMORY', 'false').lower() == 'true'

    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    MEMORY_DB_PATH = os.getenv('MEMORY_DB_PATH', '.chroma_db')

config = AgentConfig()

# print("--- Agent Configuration ---")
# print(f"Model: {config.MODEL_NAME}")
# print(f"Memory Enabled: {config.ENABLE_MEMORY}")
# print("-------------------------")