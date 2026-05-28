# Athen Agents 🏛️

Athen Agents is an autonomous, self-learning CLI agentic harness designed for software development and automation. Inspired by Nous Research's Hermes Agent, it features an interactive split-pane TUI (inspired by Grok Build) and incorporates an **LLM Wiki** to build a compounding long-term memory second-brain.

---

## Key Features

1. **Self-Learning Skills**: Synthesizes successful operations into plain Markdown skill files (`~/.athen/skills/`) and retrieves them when related tasks are requested.
2. **LLM Wiki Memory**: Operates a persistent, compounding second-brain knowledge base in Markdown (`~/.athen/wiki/`) using Ingest, Query, and Lint pipelines.
3. **Reasoning `/goal` Mode**: Runs an autonomous, long-horizon iteration loop to solve complex tasks.
4. **Sub-Agent Multitasking**: Spawns independent sub-agents executing in parallel to gather research or verify code under `/goal` workflows.
5. **Standardized 2026 Models**: Out-of-the-box support for direct APIs and OpenRouter carrying the latest 2026 frontier models (GPT-5.5, Claude 4.7 Opus, Gemini 3.5 Flash, DeepSeek V4 Pro).
6. **Built-in & MCP Tools**: Integrated filesystem, shell execution, and DuckDuckGo search tools, plus a lightweight stdio-based Model Context Protocol (MCP) client.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Vaskrokodile/athen-agents.git
cd athen-agents

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Quick Start

Make sure your API keys are set in your environment:
```bash
export OPENROUTER_API_KEY="your_openrouter_key"
export ANTHROPIC_API_KEY="your_anthropic_key"
```

Then start the TUI:
```bash
# Starts TUI using OpenRouter default model
athen

# List available models
athen --list-models

# Start with a specific model
athen --provider anthropic --model claude-4.7-opus
```
