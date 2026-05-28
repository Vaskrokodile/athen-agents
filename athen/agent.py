import json
import asyncio
from typing import List, Dict, Any, Callable, Optional
from athen.llm import LLMClient
from athen.tools import ToolManager
from athen.wiki import LLMWiki
from athen.skills import SkillsEngine
from athen.config import MCP_CONFIG_FILE

class AthenAgent:
    def __init__(
        self,
        provider: str,
        model: Optional[str] = None,
        on_status_update: Optional[Callable[[str], None]] = None,
        on_subagent_update: Optional[Callable[[str, str], None]] = None
    ):
        self.llm_client = LLMClient(provider, model)
        self.tools_manager = ToolManager()
        self.wiki = LLMWiki(self.llm_client)
        self.skills = SkillsEngine()
        
        self.on_status = on_status_update or (lambda s: None)
        self.on_subagent = on_subagent_update or (lambda name, status: None)
        
        # Load MCP configs
        self.tools_manager.load_mcp_servers(MCP_CONFIG_FILE)
        
        self.history = []
        self.active_subagents = []

    def get_base_system_prompt(self, reasoning_mode: bool = False) -> str:
        base = (
            "You are Athen Agents, a powerful autonomous AI agent CLI harness.\n"
            "You have direct access to system tools: read_file, write_file, list_dir, run_command, and web_search.\n"
            "Always follow engineering best practices, verify your outputs, and write clean, complete code.\n"
            "Keep files neat, write detailed comments where appropriate, and do not use placeholders."
        )
        if reasoning_mode:
            base += (
                "\n\n=== REASONING MODE /GOAL EXECUTIVE DIRECTIVES ===\n"
                "1. You are running in long-horizon reasoning mode designed for complex coding tasks.\n"
                "2. Break down the user's goal into a checklist. Plan first, then execute step-by-step.\n"
                "3. Verify your work using automated commands or tests. If errors occur, analyze them, fix, and re-test.\n"
                "4. You are authorized to run without requesting user permission for each step. Proceed autonomously.\n"
                "5. You can spawn background SUB-AGENTS to perform parallel tasks by outputting the 'launch_subagent' tool call.\n"
                "6. Continue looping and refining until the task is completely finished. Never give up."
            )
        return base

    async def step(self, user_input: str, is_goal: bool = False) -> str:
        """
        Take a step in the conversation. Handles LLM queries, tool execution loops,
        wiki updates, and skill invocation.
        """
        self.on_status("Searching long-term memory (LLM Wiki)...")
        # 1. Retrieve Wiki long-term memories
        wiki_context = self.wiki.query(user_input)
        
        # 2. Retrieve Relevant Skills
        skills_context = self.skills.query_skills(user_input)
        
        # 3. Assemble system prompt
        system_prompt = self.get_base_system_prompt(reasoning_mode=is_goal)
        if wiki_context:
            system_prompt += f"\n\n== RELEVANT WIKI ENTRIES FROM SECOND BRAIN ==\n{wiki_context}"
        if skills_context:
            system_prompt += f"\n{skills_context}"
            
        self.history.append({"role": "user", "content": user_input})
        
        # Add local launch_subagent tool if in goal/reasoning mode
        tools_list = self.tools_manager.get_tool_schemas()
        if is_goal:
            tools_list.append({
                "name": "launch_subagent",
                "description": "Spawn a background sub-agent to handle a sub-task concurrently.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Unique identifier for this sub-agent"},
                        "task": {"type": "string", "description": "Specific instruction for the sub-agent"}
                    },
                    "required": ["name", "task"]
                }
            })

        max_iterations = 20 if is_goal else 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            self.on_status(f"Generating LLM response (iteration {iteration})...")
            
            res = await self.llm_client.generate(
                messages=self.history,
                system_prompt=system_prompt,
                tools=tools_list
            )
            
            if res.get("content"):
                self.history.append({"role": "assistant", "content": res["content"]})
                
            tool_calls = res.get("tool_calls", [])
            if not tool_calls:
                # No more tools to run, break out of loop
                self.on_status("Finished step.")
                # Auto-ingest new user/assistant messages to Wiki memory in background
                asyncio.create_task(self.wiki.ingest("User Conversation Step", f"User: {user_input}\nAssistant: {res.get('content') or ''}"))
                return res.get("content") or "Step completed successfully."

            # Execute tool calls
            for tc in tool_calls:
                tc_id = tc["id"]
                tc_name = tc["name"]
                tc_args = tc["arguments"]
                
                self.on_status(f"Executing tool: {tc_name}...")
                
                if tc_name == "launch_subagent":
                    # Handle sub-agent execution
                    sub_name = tc_args["name"]
                    sub_task = tc_args["task"]
                    result = await self._spawn_subagent(sub_name, sub_task)
                else:
                    result = await self.tools_manager.execute_tool(tc_name, tc_args)
                
                # Append tool call result to conversation
                # For OpenAI compatibility
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": tc_name,
                    "content": result
                })
                
        self.on_status("Maximum reasoning loop iteration reached.")
        return "Reasoning limit reached."

    async def _spawn_subagent(self, name: str, task: str) -> str:
        """Spawn a background sub-agent to multi-task."""
        self.on_subagent(name, "Spawning...")
        self.active_subagents.append({"name": name, "task": task, "status": "Running"})
        
        # Instantiate another agent to run in background
        subagent = AthenAgent(
            provider=self.llm_client.provider,
            model=self.llm_client.model,
            on_status_update=lambda s: self.on_subagent(name, s)
        )
        
        # Run sub-agent step in background task
        async def run_sub():
            try:
                self.on_subagent(name, "Executing Task...")
                result = await subagent.step(task, is_goal=False)
                self.on_subagent(name, "Completed")
                return result
            except Exception as e:
                self.on_subagent(name, f"Failed: {e}")
                return f"Subagent failed: {e}"

        # We run it and wait for results (or return immediately, but since LLM is waiting
        # for tool result, we await the sub-agent execution here synchronously relative to tool loop,
        # but it executes as a distinct agent thread context)
        result = await run_sub()
        return f"Subagent '{name}' completed task with result:\n{result}"
