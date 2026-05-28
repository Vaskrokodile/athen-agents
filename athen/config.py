import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from current directory or home directory
load_dotenv()
load_dotenv(Path.home() / ".env")

# Base directory for Athen Agent storage
ATHEN_DIR = Path.home() / ".athen"
WIKI_DIR = ATHEN_DIR / "wiki"
SKILLS_DIR = ATHEN_DIR / "skills"
CONFIG_FILE = ATHEN_DIR / "config.json"
MCP_CONFIG_FILE = ATHEN_DIR / "mcp_config.json"

# Ensure directories exist
WIKI_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

# Latest 2026 Models registry and documentation
MODELS_2026 = {
    "openrouter": {
        "description": "Unified API gateway hosting 100s of models.",
        "models": {
            "openrouter/auto": "Auto-selects optimal model based on prompt size",
            "openai/gpt-5.5": "GPT-5.5 flagship agentic model",
            "openai/gpt-5.5-instant": "GPT-5.5 cost-effective speed model",
            "anthropic/claude-4.7-opus": "Frontier model for complex reasoning and coding",
            "google/gemini-3.5-flash": "Fast, high-efficiency multimodal model",
            "google/gemini-3.1-pro": "1M+ token context flagship reasoning model",
            "deepseek/deepseek-v4-pro": "Open-weight reasoning flagship"
        },
        "default": "openai/gpt-5.5"
    },
    "anthropic": {
        "description": "Direct Anthropic API.",
        "models": {
            "claude-4.7-opus": "Frontier coding and reasoning flagship",
            "claude-3.5-sonnet": "Highly reliable general developer assistant",
            "claude-3.5-haiku": "Fast low-latency tool user"
        },
        "default": "claude-4.7-opus"
    },
    "openai": {
        "description": "Direct OpenAI API.",
        "models": {
            "gpt-5.5": "GPT-5.5 flagship agentic model",
            "gpt-5.5-instant": "GPT-5.5 fast reasoning model",
            "o3-mini": "Reasoning mini-model"
        },
        "default": "gpt-5.5"
    },
    "google": {
        "description": "Direct Google Gemini API.",
        "models": {
            "gemini-3.5-flash": "Ultra-fast developer assistant",
            "gemini-3.1-pro": "Long-context reasoning engine"
        },
        "default": "gemini-3.5-flash"
    },
    "deepseek": {
        "description": "Direct DeepSeek API.",
        "models": {
            "deepseek-v4-pro": "DeepSeek's 2026 reasoning model",
            "deepseek-coder": "Specialized coding agentic model"
        },
        "default": "deepseek-v4-pro"
    }
}

def get_api_key(provider: str) -> str:
    """Retrieve API key for provider from environment variables."""
    provider = provider.lower()
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY") or ""
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY") or ""
    elif provider == "openai":
        return os.getenv("OPENAI_API_KEY") or ""
    elif provider == "google":
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    elif provider == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY") or ""
    return ""

def get_default_model(provider: str) -> str:
    """Return default model for a given provider."""
    provider = provider.lower()
    if provider in MODELS_2026:
        return MODELS_2026[provider]["default"]
    return ""
