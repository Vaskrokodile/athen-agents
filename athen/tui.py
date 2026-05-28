import os
from pathlib import Path
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Static, Label, ListView, ListItem, Button, ContentSwitcher
from textual.reactive import reactive
from textual.binding import Binding

from athen.agent import AthenAgent
from athen.config import WIKI_DIR, SKILLS_DIR, MODELS_2026, get_api_key

ASCII_LOGO = """
  █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗
 ██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║
 ███████║   ██║   ███████║█████╗  ██╔██╗ ██║
 ██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║
 ██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║
 ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝
"""

ASCII_COLISEUM = """
      ___________________________
    //   ___   ___   ___   ___   \\\\
   ||   |   | |   | |   | |   |   ||
   ||   |___| |___| |___| |___|   ||
   ||   [___] [___] [___] [___]   ||
   ||   |   | |   | |   | |   |   ||
    \\\\___|___|_|___|_|___|_|___|___//
"""

CSS_STYLING = """
Screen {
    background: #0f141c;
    color: #e6edf3;
}

#header-area {
    height: 14;
    background: #161b22;
    border-bottom: solid #ffffff;
    align: center middle;
    text-align: center;
}

#logo {
    color: #ffffff;
    text-style: bold;
    height: 6;
}

#coliseum {
    color: #8b949e;
    height: 7;
}

#main-container {
    height: 1fr;
    width: 100%;
}

#sidebar {
    width: 25%;
    height: 100%;
    border-right: solid #30363d;
    background: #161b22;
    padding: 1;
}

#sidebar-title {
    text-style: bold;
    color: #8b949e;
    margin-bottom: 1;
}

.channel-item {
    padding: 1 2;
    background: #1f242c;
    border: solid #30363d;
    margin-bottom: 1;
    color: #c9d1d9;
}

.channel-item:hover {
    background: #ffffff;
    color: #000000;
}

#detail-switcher {
    width: 75%;
    height: 100%;
}

/* Page views */
.view-panel {
    width: 100%;
    height: 100%;
    padding: 1;
}

.view-title {
    text-style: bold;
    color: #ffffff;
    margin-bottom: 1;
    border-bottom: solid #30363d;
    padding-bottom: 1;
}

#chat-log {
    height: 1fr;
    background: #0d1117;
    border: solid #30363d;
    padding: 1;
    color: #ffffff;
    margin-bottom: 1;
}

#status-bar {
    height: 3;
    background: #1f242c;
    border-top: solid #30363d;
    color: #8b949e;
    content-align: left middle;
    padding-left: 2;
}

#input-area {
    height: 4;
    background: #0f141c;
    padding: 0;
}

#user-input {
    border: solid #ffffff;
    background: #0d1117;
    color: #ffffff;
}

#user-input:focus {
    border: double #ffffff;
}

/* Autocomplete popup */
#autocomplete-box {
    background: #1f242c;
    border: solid #ffffff;
    height: auto;
    max-height: 10;
    color: #ffffff;
    padding: 0 1;
    display: none;
}

.autocomplete-item {
    padding: 0 1;
    color: #e6edf3;
}

.autocomplete-item:hover {
    background: #ffffff;
    color: #000000;
}

/* Settings fields */
.settings-input {
    margin-bottom: 1;
    border: solid #30363d;
    background: #0d1117;
    color: #ffffff;
}

#save-settings-btn {
    background: #ffffff;
    color: #000000;
    margin-top: 1;
}

#graph-view-area {
    background: #0d1117;
    border: solid #30363d;
    height: 1fr;
    padding: 1;
    overflow-y: scroll;
}
"""

class AthenTUI(App):
    CSS = CSS_STYLING
    
    BINDINGS = [
        Binding("q", "quit", "Quit Athen", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("c", "clear_chat", "Clear Chat", show=True),
        Binding("l", "run_lint", "Lint Wiki", show=True)
    ]

    status_message = reactive("Ready.")
    subagent_list = reactive({})
    active_view = reactive("chat")
    is_plan_only = reactive(False)

    def __init__(self, provider: str, model: str = None):
        super().__init__()
        self.provider = provider
        self.model = model
        self.agent = AthenAgent(
            provider=provider,
            model=model,
            on_status_update=self.update_status,
            on_subagent_update=self.update_subagent
        )

    def compose(self) -> ComposeResult:
        # Top Header Banner with 3D Logo and Coliseum
        with Vertical(id="header-area"):
            yield Static(ASCII_LOGO, id="logo")
            yield Static(ASCII_COLISEUM, id="coliseum")
            
        with Horizontal(id="main-container"):
            # Left Sidebar (Channels selection list)
            with Vertical(id="sidebar"):
                yield Label("[CHANNELS]", id="sidebar-title")
                with ListView(id="channel-list"):
                    yield ListItem(Label("[Chat] Conversation"), id="chan-chat", classes="channel-item")
                    yield ListItem(Label("[Memory] LLM Wiki Graph"), id="chan-wiki", classes="channel-item")
                    yield ListItem(Label("[Skills] Learned Skills"), id="chan-skills", classes="channel-item")
                    yield ListItem(Label("[Agents] Sub-Agents Track"), id="chan-subagents", classes="channel-item")
                    yield ListItem(Label("[Settings] API Keys"), id="chan-settings", classes="channel-item")
                
            # Right Panel switcher
            with ContentSwitcher(id="detail-switcher", initial="view-chat"):
                # 1. Chat View
                with Vertical(id="view-chat", classes="view-panel"):
                    yield Label("[CHAT SESSION]", classes="view-title")
                    yield RichLog(id="chat-log", wrap=True, highlight=True, max_lines=1000)
                    # Autocomplete Float Box
                    with ListView(id="autocomplete-box"):
                        yield ListItem(Label("/goal [task] - Launch reasoning code goal"), id="ac-goal", classes="autocomplete-item")
                        yield ListItem(Label("/plan [task] - Plan-only mode"), id="ac-plan", classes="autocomplete-item")
                        yield ListItem(Label("/model - Click to select model"), id="ac-model", classes="autocomplete-item")
                    with Vertical(id="input-area"):
                        yield Input(placeholder="Type message or '/' for commands...", id="user-input")
                
                # 2. LLM Wiki Graph View
                with Vertical(id="view-wiki", classes="view-panel"):
                    yield Label("[NEURAL MEMORY GRAPH]", classes="view-title")
                    yield Static(id="graph-view-area")

                # 3. Skills View
                with Vertical(id="view-skills", classes="view-panel"):
                    yield Label("[SYNTHESIZED SKILLS]", classes="view-title")
                    yield RichLog(id="skills-view-area", wrap=True, highlight=True)

                # 4. Sub-Agents View
                with Vertical(id="view-subagents", classes="view-panel"):
                    yield Label("[SUB-AGENTS RUNNING]", classes="view-title")
                    yield RichLog(id="subagents-view-area", wrap=True, highlight=True)

                # 5. Settings View
                with Vertical(id="view-settings", classes="view-panel"):
                    yield Label("[SETTINGS - API KEYS]", classes="view-title")
                    yield Label("OpenRouter API Key:")
                    yield Input(placeholder="OPENROUTER_API_KEY", id="set-openrouter", classes="settings-input")
                    yield Label("Anthropic API Key:")
                    yield Input(placeholder="ANTHROPIC_API_KEY", id="set-anthropic", classes="settings-input")
                    yield Label("OpenAI API Key:")
                    yield Input(placeholder="OPENAI_API_KEY", id="set-openai", classes="settings-input")
                    yield Label("Gemini API Key:")
                    yield Input(placeholder="GEMINI_API_KEY", id="set-gemini", classes="settings-input")
                    yield Label("DeepSeek API Key:")
                    yield Input(placeholder="DEEPSEEK_API_KEY", id="set-deepseek", classes="settings-input")
                    yield Button("Save API Keys", id="save-settings-btn")

        yield Label("Status: Ready", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Athen Agents CLI Harness - {self.model or 'Default'}"
        self.chat_log = self.query_one("#chat-log", RichLog)
        self.chat_log.write(Text.from_markup("Welcome to [bold #ffffff]Athen Agents[/bold #ffffff]. Powered by the latest 2026 reasoning models."))
        self.chat_log.write(Text.from_markup("Type a prompt or try: [bold #ffffff]/goal build a web app[/bold #ffffff] to launch long-horizon coding loop."))
        
        # Populate Settings values
        self.query_one("#set-openrouter", Input).value = os.getenv("OPENROUTER_API_KEY") or ""
        self.query_one("#set-anthropic", Input).value = os.getenv("ANTHROPIC_API_KEY") or ""
        self.query_one("#set-openai", Input).value = os.getenv("OPENAI_API_KEY") or ""
        self.query_one("#set-gemini", Input).value = os.getenv("GEMINI_API_KEY") or ""
        self.query_one("#set-deepseek", Input).value = os.getenv("DEEPSEEK_API_KEY") or ""

        self.update_all_views()

    def update_status(self, status: str) -> None:
        self.status_message = status
        self.query_one("#status-bar", Label).update(f"Status: {status}")

    def update_subagent(self, name: str, status: str) -> None:
        new_list = dict(self.subagent_list)
        new_list[name] = status
        self.subagent_list = new_list
        self.update_subagents_view()

    def update_all_views(self) -> None:
        self.update_wiki_graph()
        self.update_skills_view()
        self.update_subagents_view()

    def update_wiki_graph(self) -> None:
        wiki_data = self.agent.wiki.get_links()
        nodes = wiki_data.get("nodes", [])
        links = wiki_data.get("links", [])
        
        graph_str = "● NEURAL KNOWLEDGE GRAPH MAP\n===========================\n\n"
        if not nodes:
            graph_str += "Graph is empty. Start a conversation to populate memory."
        else:
            adj = {n: [] for n in nodes}
            for link in links:
                adj[link["source"]].append(link["target"])
                
            visited = set()
            for root in nodes:
                if root not in visited:
                    graph_str += f"● {root}\n"
                    visited.add(root)
                    for child in adj[root]:
                        if child not in visited:
                            graph_str += f"   ├───► ● {child}\n"
                            visited.add(child)
                            for subchild in adj.get(child, []):
                                if subchild not in visited:
                                    graph_str += f"   │      └───► ● {subchild}\n"
                                    visited.add(subchild)
            
            for n in nodes:
                if n not in visited:
                    graph_str += f"● {n}\n"
                    
        self.query_one("#graph-view-area", Static).update(graph_str)

    def update_skills_view(self) -> None:
        area = self.query_one("#skills-view-area", RichLog)
        area.clear()
        skill_files = list(SKILLS_DIR.glob("*.md"))
        if not skill_files:
            area.write("No self-learned skills synthesized yet.")
            return
        for file in skill_files:
            content = file.read_text(encoding="utf-8", errors="replace")
            area.write(f"--- SKILL FILE: {file.name} ---\n{content}\n")

    def update_subagents_view(self) -> None:
        area = self.query_one("#subagents-view-area", RichLog)
        area.clear()
        if not self.subagent_list:
            area.write("No active background sub-agents.")
            return
        for sub_name, sub_status in self.subagent_list.items():
            area.write(f"- Subagent [bold #ffffff]{sub_name}[/bold #ffffff]: {sub_status}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        switcher = self.query_one("#detail-switcher", ContentSwitcher)
        
        if item_id == "chan-chat":
            switcher.current = "view-chat"
        elif item_id == "chan-wiki":
            self.update_wiki_graph()
            switcher.current = "view-wiki"
        elif item_id == "chan-skills":
            self.update_skills_view()
            switcher.current = "view-skills"
        elif item_id == "chan-subagents":
            self.update_subagents_view()
            switcher.current = "view-subagents"
        elif item_id == "chan-settings":
            switcher.current = "view-settings"
            
        # Autocomplete handle
        elif item_id == "ac-goal":
            self.query_one("#user-input", Input).value = "/goal "
            self.query_one("#user-input", Input).focus()
            self.query_one("#autocomplete-box", ListView).styles.display = "none"
        elif item_id == "ac-plan":
            self.query_one("#user-input", Input).value = "/plan "
            self.query_one("#user-input", Input).focus()
            self.query_one("#autocomplete-box", ListView).styles.display = "none"
        elif item_id == "ac-model":
            # Replace ListView options with models!
            self.show_model_selection_dropdown()
        elif item_id.startswith("select-model:"):
            model_name = item_id.split(":", 1)[1]
            self.switch_to_model(model_name)
            self.query_one("#user-input", Input).value = ""
            self.query_one("#autocomplete-box", ListView).styles.display = "none"

    def show_model_selection_dropdown(self) -> None:
        box = self.query_one("#autocomplete-box", ListView)
        box.clear()
        
        # Add a back button
        box.append(ListItem(Label("<- Back to Commands"), id="ac-back", classes="autocomplete-item"))
        
        # Add all available models
        for provider, info in MODELS_2026.items():
            for model_id in info["models"].keys():
                box.append(ListItem(Label(f"Model: {model_id}"), id=f"select-model:{model_id}", classes="autocomplete-item"))

    def switch_to_model(self, model_name: str) -> None:
        # Auto-detect provider based on chosen model
        provider = "openrouter"
        model_to_use = model_name
        
        if "claude" in model_name:
            provider = "anthropic"
        elif "gemini" in model_name:
            provider = "google"
        elif "deepseek" in model_name:
            provider = "deepseek"
            if model_name.startswith("deepseek/"):
                model_to_use = model_name.split("/", 1)[1]
        elif "gpt" in model_name:
            provider = "openai"
            if model_name.startswith("openai/"):
                model_to_use = model_name.split("/", 1)[1]

        # Apply settings
        self.agent.llm_client.provider = provider
        self.agent.llm_client.model = model_to_use
        self.agent.llm_client.api_key = get_api_key(provider)
        
        self.chat_log.write(Text.from_markup(f"\n[bold #ffffff][MODEL CHANGED]:[/bold #ffffff] Switched to provider [bold]{provider}[/bold], model [bold]{model_to_use}[/bold]"))
        self.update_status(f"Provider: {provider} | Model: {model_to_use}")

    def on_input_changed(self, event: Input.Changed) -> None:
        val = event.value
        box = self.query_one("#autocomplete-box", ListView)
        if val == "/":
            box.clear()
            box.append(ListItem(Label("/goal [task] - Launch reasoning code goal"), id="ac-goal", classes="autocomplete-item"))
            box.append(ListItem(Label("/plan [task] - Plan-only mode"), id="ac-plan", classes="autocomplete-item"))
            box.append(ListItem(Label("/model - Click to select model"), id="ac-model", classes="autocomplete-item"))
            box.styles.display = "block"
        elif not val.startswith("/"):
            box.styles.display = "none"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return
            
        event.input.value = ""
        self.query_one("#autocomplete-box", ListView).styles.display = "none"
        self.chat_log.write(Text.from_markup(f"\n[bold #ffffff]>>> User:[/bold #ffffff] {user_text}"))

        is_goal = False
        is_plan = False
        
        if user_text.startswith("/goal "):
            is_goal = True
            prompt = user_text[6:].strip()
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff][GOAL RUNNING]:[/bold #ffffff] {prompt}"))
        elif user_text.startswith("/plan "):
            is_plan = True
            prompt = user_text[6:].strip()
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff][PLANNING MODE RUNNING]:[/bold #ffffff] {prompt}"))
        elif user_text.startswith("/model"):
            parts = user_text.split(" ", 1)
            if len(parts) > 1:
                self.switch_to_model(parts[1].strip())
            else:
                self.show_model_selection_dropdown()
                self.query_one("#autocomplete-box", ListView).styles.display = "block"
            return
        else:
            prompt = user_text

        self.is_plan_only = is_plan
        self.run_worker(self.execute_agent_loop(prompt, is_goal or is_plan))

    async def execute_agent_loop(self, prompt: str, is_goal: bool) -> None:
        try:
            self.update_status("Thinking...")
            if self.is_plan_only:
                prompt = f"PLAN ONLY: Create a complete implementation plan for this goal. Do not run any code write operations: {prompt}"
            response = await self.agent.step(prompt, is_goal=is_goal)
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff]🤖 Athen Agent:[/bold #ffffff]\n{response}"))
            self.update_all_views()
        except Exception as e:
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff][SYSTEM ERROR]:[/bold #ffffff] {str(e)}"))
        finally:
            self.update_status(f"Provider: {self.agent.llm_client.provider} | Model: {self.agent.llm_client.model}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings-btn":
            env_path = Path.cwd() / ".env"
            openrouter = self.query_one("#set-openrouter", Input).value
            anthropic = self.query_one("#set-anthropic", Input).value
            openai = self.query_one("#set-openai", Input).value
            gemini = self.query_one("#set-gemini", Input).value
            deepseek = self.query_one("#set-deepseek", Input).value
            
            lines = [
                f"OPENROUTER_API_KEY={openrouter}\n",
                f"ANTHROPIC_API_KEY={anthropic}\n",
                f"OPENAI_API_KEY={openai}\n",
                f"GEMINI_API_KEY={gemini}\n",
                f"DEEPSEEK_API_KEY={deepseek}\n"
            ]
            env_path.write_text("".join(lines))
            
            os.environ["OPENROUTER_API_KEY"] = openrouter
            os.environ["ANTHROPIC_API_KEY"] = anthropic
            os.environ["OPENAI_API_KEY"] = openai
            os.environ["GEMINI_API_KEY"] = gemini
            os.environ["DEEPSEEK_API_KEY"] = deepseek
            
            # Reload key for current active provider
            self.agent.llm_client.api_key = get_api_key(self.agent.llm_client.provider)
            
            self.update_status("API Keys Saved successfully.")
            self.chat_log.write(Text.from_markup("\n[bold #ffffff]System status:[/bold #ffffff] API keys saved to .env and loaded successfully."))

    def action_clear_chat(self) -> None:
        self.chat_log.clear()
        self.chat_log.write(Text.from_markup("Chat cleared."))

    async def action_run_lint(self) -> None:
        self.update_status("Linting LLM Wiki database...")
        res = await self.agent.wiki.lint()
        self.chat_log.write(Text.from_markup(f"\n[bold #ffffff]System memory linter:[/bold #ffffff]\n{res}"))
        self.update_all_views()
        self.update_status(f"Provider: {self.agent.llm_client.provider} | Model: {self.agent.llm_client.model}")
