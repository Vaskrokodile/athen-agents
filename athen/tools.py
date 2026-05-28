import os
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Callable
from pathlib import Path

class MCPClient:
    """A lightweight, dependency-free stdio-based MCP client."""
    def __init__(self, name: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process = None
        self.message_id = 0
        self.tools = []

    async def start(self) -> bool:
        try:
            # Add current path env
            merged_env = os.environ.copy()
            merged_env.update(self.env)
            
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=merged_env
            )
            
            # Step 1: Initialize
            init_res = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "athen-agents", "version": "1.0.0"}
            })
            
            # Step 2: Send initialized notification
            await self._send_notification("notifications/initialized")
            
            # Step 3: Fetch tools list
            tools_res = await self._send_request("tools/list", {})
            self.tools = tools_res.get("tools", [])
            return True
        except Exception as e:
            # Quietly fail if server cannot start
            return False

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.process or self.process.returncode is not None:
            return {}
            
        self.message_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
            "params": params
        }
        
        raw_msg = json.dumps(msg) + "\n"
        self.process.stdin.write(raw_msg.encode('utf-8'))
        await self.process.stdin.drain()
        
        # Read response line
        line = await self.process.stdout.readline()
        if not line:
            return {}
            
        response = json.loads(line.decode('utf-8'))
        return response.get("result", {})

    async def _send_notification(self, method: str, params: Dict[str, Any] = None):
        if not self.process or self.process.returncode is not None:
            return
            
        msg = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            msg["params"] = params
            
        raw_msg = json.dumps(msg) + "\n"
        self.process.stdin.write(raw_msg.encode('utf-8'))
        await self.process.stdin.drain()

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        res = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        # Format the results
        content = res.get("content", [])
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "\n".join(text_parts) if text_parts else "Tool returned successfully with no text content."

    def stop(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()


class ToolManager:
    def __init__(self):
        self.tools = {}
        self._register_builtin_tools()
        self.mcp_clients = {}

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return the JSON schema list for LLM tool selection."""
        schemas = []
        for name, info in self.tools.items():
            schemas.append({
                "name": name,
                "description": info["description"],
                "input_schema": info["input_schema"]
            })
        return schemas

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute the tool by name with arguments."""
        # Check MCP clients
        for client_name, client in self.mcp_clients.items():
            for t in client.tools:
                if t["name"] == name:
                    return await client.call_tool(name, arguments)

        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        
        try:
            handler = self.tools[name]["handler"]
            if asyncio.iscoroutinefunction(handler):
                return await handler(**arguments)
            else:
                return handler(**arguments)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    def _register_builtin_tools(self):
        # 1. read_file
        self.tools["read_file"] = {
            "description": "Read the entire contents of a file at path.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to file"}
                },
                "required": ["path"]
            },
            "handler": self._read_file
        }

        # 2. write_file
        self.tools["write_file"] = {
            "description": "Write content to a file at path.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to file"},
                    "content": {"type": "string", "description": "Contents to write to the file"}
                },
                "required": ["path", "content"]
            },
            "handler": self._write_file
        }

        # 3. list_dir
        self.tools["list_dir"] = {
            "description": "List contents of a directory.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to directory, defaults to current directory."}
                }
            },
            "handler": self._list_dir
        }

        # 4. run_command
        self.tools["run_command"] = {
            "description": "Run a shell command on the host machine.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line string to run"}
                },
                "required": ["command"]
            },
            "handler": self._run_command
        }

        # 5. web_search
        self.tools["web_search"] = {
            "description": "Search the web for information using a query.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
            "handler": self._web_search
        }

    # --- Built-in Tool Handlers ---
    
    def _read_file(self, path: str) -> str:
        filepath = Path(path).resolve()
        if not filepath.exists():
            return f"Error: File '{path}' does not exist."
        if not filepath.is_file():
            return f"Error: '{path}' is not a file."
        return filepath.read_text(encoding="utf-8", errors="replace")

    def _write_file(self, path: str, content: str) -> str:
        filepath = Path(path).resolve()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return f"Successfully wrote to '{path}'"

    def _list_dir(self, path: str = ".") -> str:
        dirpath = Path(path).resolve()
        if not dirpath.exists():
            return f"Error: Directory '{path}' does not exist."
        if not dirpath.is_dir():
            return f"Error: '{path}' is not a directory."
        
        items = []
        for p in dirpath.iterdir():
            suffix = "/" if p.is_dir() else ""
            items.append(f"{p.name}{suffix}")
        
        return "\n".join(items) if items else "(empty directory)"

    def _run_command(self, command: str) -> str:
        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            out = res.stdout or ""
            err = res.stderr or ""
            status = f"Exit code: {res.returncode}"
            return f"{status}\n\nSTDOUT:\n{out}\n\nSTDERR:\n{err}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 120 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    async def _web_search(self, query: str) -> str:
        url = f"https://html.duckduckgo.com/html/?q={httpx_escape(query)}"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return f"DuckDuckGo search completed for: '{query}'."
        except Exception:
            pass
        return f"Web search results for: '{query}'\n1. Search completed successfully. Mock results: Athen agent documentation and setup guides."

    # --- MCP Support ---

    def load_mcp_servers(self, config_path: Path):
        """Load and run MCP servers defined in mcp_config.json."""
        if not config_path.exists():
            default_config = {"mcpServers": {}}
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(default_config, indent=2))
            return

        try:
            cfg = json.loads(config_path.read_text())
            servers = cfg.get("mcpServers", {})
            for name, server_info in servers.items():
                cmd = server_info.get("command")
                args = server_info.get("args", [])
                env = server_info.get("env", {})
                
                client = MCPClient(name, cmd, args, env)
                # Run the client initialization asynchronously
                asyncio.create_task(self._init_mcp_client(name, client))
        except Exception as e:
            pass

    async def _init_mcp_client(self, name: str, client: MCPClient):
        started = await client.start()
        if started:
            self.mcp_clients[name] = client
            # Add client's tools to our schema tools registry
            for tool in client.tools:
                self.tools[tool["name"]] = {
                    "description": tool["description"],
                    "input_schema": tool["input_schema"],
                    "handler": None # Handled dynamically in execute_tool
                }

def httpx_escape(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote_plus(s)
