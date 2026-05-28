import sys
import argparse
from athen.config import MODELS_2026, get_default_model
from athen.tui import AthenTUI

def print_models():
    """Print registered 2026 models nicely."""
    print("========================================")
    print("          ATHEN AGENTS 2026 MODELS       ")
    print("========================================")
    for provider, info in MODELS_2026.items():
        print(f"\nProvider: {provider.upper()}")
        print(f"Description: {info['description']}")
        print("Models:")
        for model_id, desc in info["models"].items():
            default_marker = " (default)" if model_id == info["default"] else ""
            print(f"  - {model_id:<30} {desc}{default_marker}")
    print("\nConfigure API keys in your environment (e.g. OPENROUTER_API_KEY, ANTHROPIC_API_KEY, etc.)")

def main():
    parser = argparse.ArgumentParser(description="Athen Agents: A self-learning CLI Agentic Harness.")
    parser.add_argument(
        "--provider", "-p",
        choices=["openrouter", "openai", "anthropic", "google", "deepseek"],
        default="openrouter",
        help="LLM provider (default: openrouter)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Specify the LLM model to use (defaults to provider's default 2026 model)"
    )
    parser.add_argument(
        "--list-models", "-l",
        action="store_true",
        help="List available 2026 frontier models for each provider"
    )

    args = parser.parse_args()

    if args.list_models:
        print_models()
        sys.exit(0)

    # Determine default model if not supplied
    model = args.model or get_default_model(args.provider)

    print(f"Launching Athen Agents TUI with provider: {args.provider}, model: {model}")
    app = AthenTUI(provider=args.provider, model=model)
    app.run()

if __name__ == "__main__":
    main()
