import os
import json
import urllib.request
import urllib.error
import sys

# Schema definitions for the Agent
TOOLS_SCHEMA = [
    {
        "name": "disk",
        "description": "Manage disk space, caches, and files.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["scan", "clean", "explore", "large_files"]},
                "target": {"type": "string", "description": "Cache ID (pip, npm) or path/size"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "memory",
        "description": "Second Brain: Notes and Command History.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add_note", "get_notes", "sync", "search", "scrub"]},
                "content": {"type": "string", "description": "Note text or search query"},
                "tags": {"type": "string", "description": "Comma-separated tags"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "system",
        "description": "System maintenance (Docker, Logs, Trash).",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["docker_prune", "vacuum_logs", "empty_trash", "apt_clean", "status"]}
            },
            "required": ["action"]
        }
    }
]

SYSTEM_PROMPT = f"""
You are AgentOS, a system administration assistant.
You have access to the following tools to manage the user's computer:
{json.dumps(TOOLS_SCHEMA, indent=2)}

RULES:
1. If the user asks to perform an action available in the tools, output a JSON object describing the tool call.
   Format: {{"tool": "module_name", "args": {{ "action": "...", ... }} }}
   Example: {{"tool": "disk", "args": {{ "action": "clean", "target": "pip" }} }}
   
2. If the user asks a general question, just answer normally.

3. If you need more information to call a tool (e.g., missing 'content' for a note), ask the user.

4. Be concise and professional.
"""

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("AGENT_API_KEY")
        # Default to OpenAI, but allow override for Local/Groq/etc.
        self.api_url = os.getenv("AGENT_API_URL", "https://api.openai.com/v1/chat/completions")
        self.model = os.getenv("AGENT_MODEL", "gpt-4o-mini") 
        
        if not self.api_key:
            print("Warning: AGENT_API_KEY not set. Chat mode will be simulated.")

    def chat(self, user_input, history=[]):
        """
        Sends message to LLM. Returns (text_response, tool_call_dict).
        """
        if not self.api_key:
            return self._simulation_mode(user_input)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_input}]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"} 
        }

        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.load(response)
                content = result['choices'][0]['message']['content']
                
                # Check if it's a tool call (JSON)
                try:
                    data = json.loads(content)
                    if "tool" in data and "args" in data:
                        return None, data
                    return content, None # Just text
                except:
                    return content, None
                    
        except Exception as e:
            return f"Error contacting LLM: {e}", None

    def _simulation_mode(self, user_input):
        """Fallback for when no API key is present."""
        user_input = user_input.lower()
        
        # Simple keyword matching for demo purposes
        if "clean" in user_input and "pip" in user_input:
            return None, {"tool": "disk", "args": {"action": "clean", "target": "pip"}}
        if "disk" in user_input and "scan" in user_input:
            return None, {"tool": "disk", "args": {"action": "scan"}}
        if "note" in user_input and "add" in user_input:
            # Extract basic content
            return None, {"tool": "memory", "args": {"action": "add_note", "content": "Simulated Note", "tags": "demo"}}
        if "docker" in user_input:
            return None, {"tool": "system", "args": {"action": "docker_prune"}}
            
        return "I am in simulation mode (No API KEY). I can only respond to basic keywords like 'clean pip', 'scan disk', 'add note'. Set AGENT_API_KEY to use full intelligence.", None
