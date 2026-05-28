import os
from pathlib import Path
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Static, Label, ListView, ListItem
from textual.reactive import reactive
from textual.binding import Binding

from athen.agent import AthenAgent
from athen.config import WIKI_DIR, SKILLS_DIR

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
    width: 28%;
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

#chat-panel {
    width: 72%;
    height: 100%;
    padding: 1;
}

#chat-log {
    height: 1fr;
    background: #0d1117;
    border: solid #30363d;
    padding: 1;
    color: #ffffff;
}

#status-bar {
    height: 3;
    background: #1f242c;
    border-top: solid #30363d;
    color: #8b949e;
    content-align: left middle;
    padding-left: 2;
}

#input-container {
    height: auto;
    padding: 0 1;
    background: #0f141c;
}

#user-input {
    border: solid #ffffff;
    background: #0d1117;
    color: #ffffff;
}

#user-input:focus {
    border: double #ffffff;
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
    active_channel = reactive("wiki")

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
                yield Label("[CHANNELS] (Memory)", id="sidebar-title")
                with ListView(id="channel-list"):
                    yield ListItem(Label("[Memory] LLM Wiki"), id="chan-wiki", classes="channel-item")
                    yield ListItem(Label("[Skills] Self-Learned"), id="chan-skills", classes="channel-item")
                    yield ListItem(Label("[Agents] Sub-Agents"), id="chan-subagents", classes="channel-item")
                yield Static(id="sidebar-details-title", classes="channel-item")
                yield Static(id="sidebar-details", classes="channel-item")
                
            # Right/Center Chat Panel
            with Vertical(id="chat-panel"):
                yield Label("[CHAT SESSION]", id="chat-title")
                yield RichLog(id="chat-log", wrap=True, highlight=True, max_lines=1000)
                
        yield Label("Status: Ready", id="status-bar")
        
        with Container(id="input-container"):
            yield Input(placeholder="Type message or `/goal <task>` to solve complex tasks...", id="user-input")
            
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Athen Agents CLI Harness - {self.model or 'Default'}"
        self.chat_log = self.query_one("#chat-log", RichLog)
        self.chat_log.write(Text.from_markup("Welcome to [bold #ffffff]Athen Agents[/bold #ffffff]. Powered by the latest 2026 reasoning models."))
        self.chat_log.write(Text.from_markup("Type a prompt or try: [bold #ffffff]/goal build a web app[/bold #ffffff] to launch long-horizon coding loop."))
        self.update_sidebar_content()

    def update_status(self, status: str) -> None:
        self.status_message = status
        self.query_one("#status-bar", Label).update(f"Status: {status}")

    def update_subagent(self, name: str, status: str) -> None:
        new_list = dict(self.subagent_list)
        new_list[name] = status
        self.subagent_list = new_list
        if self.active_channel == "subagents":
            self.update_sidebar_content()

    def update_sidebar_content(self) -> None:
        title_el = self.query_one("#sidebar-details-title", Static)
        details_el = self.query_one("#sidebar-details", Static)

        if self.active_channel == "wiki":
            title_el.update("[MEMORIES]")
            wiki_files = list(WIKI_DIR.glob("*.md"))
            wiki_str = ""
            if not wiki_files:
                wiki_str = "No wiki files yet."
            for file in wiki_files:
                wiki_str += f"- {file.stem}\n"
            details_el.update(wiki_str)
            
        elif self.active_channel == "skills":
            title_el.update("[SKILLS]")
            skill_files = list(SKILLS_DIR.glob("*.md"))
            skills_str = ""
            if not skill_files:
                skills_str = "No learned skills yet."
            for file in skill_files:
                skills_str += f"- {file.stem}\n"
            details_el.update(skills_str)
            
        elif self.active_channel == "subagents":
            title_el.update("[SUB-AGENTS]")
            subagent_str = ""
            if not self.subagent_list:
                subagent_str = "No active sub-agents."
            for sub_name, sub_status in self.subagent_list.items():
                subagent_str += f"- {sub_name}: {sub_status}\n"
            details_el.update(subagent_str)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id == "chan-wiki":
            self.active_channel = "wiki"
        elif item_id == "chan-skills":
            self.active_channel = "skills"
        elif item_id == "chan-subagents":
            self.active_channel = "subagents"
        self.update_sidebar_content()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return
            
        event.input.value = ""
        self.chat_log.write(Text.from_markup(f"\n[bold #ffffff]>>> User:[/bold #ffffff] {user_text}"))

        is_goal = False
        if user_text.startswith("/goal "):
            is_goal = True
            prompt = user_text[6:].strip()
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff][GOAL RUNNING]:[/bold #ffffff] {prompt}"))
        else:
            prompt = user_text

        self.run_worker(self.execute_agent_loop(prompt, is_goal))

    async def execute_agent_loop(self, prompt: str, is_goal: bool) -> None:
        try:
            self.update_status("Thinking...")
            response = await self.agent.step(prompt, is_goal=is_goal)
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff]🤖 Athen Agent:[/bold #ffffff]\n{response}"))
            self.update_sidebar_content()
        except Exception as e:
            self.chat_log.write(Text.from_markup(f"\n[bold #ffffff][SYSTEM ERROR]:[/bold #ffffff] {str(e)}"))
        finally:
            self.update_status("Ready.")

    def action_clear_chat(self) -> None:
        self.chat_log.clear()
        self.chat_log.write(Text.from_markup("Chat cleared."))

    async def action_run_lint(self) -> None:
        self.update_status("Linting LLM Wiki database...")
        res = await self.agent.wiki.lint()
        self.chat_log.write(Text.from_markup(f"\n[bold #ffffff]System memory linter:[/bold #ffffff]\n{res}"))
        self.update_sidebar_content()
        self.update_status("Ready.")
