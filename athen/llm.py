import json
import httpx
from typing import List, Dict, Any, Optional
from athen.config import get_api_key

class LLMClient:
    def __init__(self, provider: str, model: str = None):
        self.provider = provider.lower()
        self.api_key = get_api_key(self.provider)
        self.model = model or self._default_model()
        self.timeout = 60.0

    def _default_model(self) -> str:
        if self.provider == "openrouter":
            return "openai/gpt-5.5"
        elif self.provider == "openai":
            return "gpt-5.5"
        elif self.provider == "anthropic":
            return "claude-4.7-opus"
        elif self.provider == "google":
            return "gemini-3.5-flash"
        elif self.provider == "deepseek":
            return "deepseek-v4-pro"
        return "gpt-5.5"

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate response from provider LLM."""
        if not self.api_key:
            raise ValueError(f"API Key for provider '{self.provider}' is not set.")

        if self.provider in ["openai", "openrouter", "deepseek", "google"]:
            return await self._call_openai_compatible(messages, system_prompt, tools, temperature)
        elif self.provider == "anthropic":
            return await self._call_anthropic(messages, system_prompt, tools, temperature)
        else:
            raise NotImplementedError(f"Provider {self.provider} not supported.")

    async def _call_openai_compatible(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float
    ) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if self.provider == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers["HTTP-Referer"] = "https://github.com/athen-agents"
            headers["X-Title"] = "Athen Agents"
        elif self.provider == "deepseek":
            url = "https://api.deepseek.com/v1/chat/completions"
        elif self.provider == "google":
            # Using Gemini's OpenAI compatibility endpoint
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

        # Format messages. Include system prompt as first message if present.
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature
        }

        if tools:
            # Convert tools to openai tool schema
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"]
                    }
                })
            payload["tools"] = openai_tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"API Error {response.status_code}: {response.text}")
            
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            
            tool_calls = []
            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    tool_calls.append({
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"])
                    })

            return {
                "content": message.get("content") or "",
                "tool_calls": tool_calls
            }

    async def _call_anthropic(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float
    ) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Filter out system messages from OpenAI format if present, system prompt passed separately in Anthropic
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                # If there's a system message in the list, combine it or use it
                if not system_prompt:
                    system_prompt = msg["content"]
                continue
            
            # Map roles: 'assistant' -> 'assistant', 'user' -> 'user'
            role = msg["role"]
            if role == "tool":
                # Convert tool output message to Anthropic format
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"]
                        }
                    ]
                })
            else:
                anthropic_messages.append({
                    "role": role,
                    "content": msg["content"]
                })

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "temperature": temperature
        }

        if system_prompt:
            payload["system"] = system_prompt

        if tools:
            anthropic_tools = []
            for t in tools:
                anthropic_tools.append({
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["input_schema"]
                })
            payload["tools"] = anthropic_tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"Anthropic API Error {response.status_code}: {response.text}")
            
            data = response.json()
            content_text = ""
            tool_calls = []
            
            for content_block in data.get("content", []):
                if content_block["type"] == "text":
                    content_text += content_block["text"]
                elif content_block["type"] == "tool_use":
                    tool_calls.append({
                        "id": content_block["id"],
                        "name": content_block["name"],
                        "arguments": content_block["input"]
                    })

            return {
                "content": content_text,
                "tool_calls": tool_calls
            }
