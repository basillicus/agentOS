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
        # Paths
        self.config_path = os.path.join(os.path.dirname(__file__), "../../data/config.json")
        
        # Load Config
        self.config = self._load_config()
        
        # Configuration Priorities: Config File > Env Var > Defaults
        self.api_key = os.getenv("AGENT_API_KEY", "ollama") 
        self.base_url = self.config.get("base_url") or os.getenv("AGENT_BASE_URL", "http://localhost:11434")
        self.model = self.config.get("model") or os.getenv("AGENT_MODEL", "llama3")
        
        # Determine endpoints based on base_url
        self._update_endpoints()

    def _update_endpoints(self):
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            self.provider = "ollama"
            self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
            self.tags_endpoint = f"{self.base_url}/api/tags"
        else:
            self.provider = "openai"
            self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
            self.tags_endpoint = f"{self.base_url}/v1/models"

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except: pass
        return {}

    def save_config(self, model=None, base_url=None):
        if model: self.model = model
        if base_url: self.base_url = base_url
        
        self.config['model'] = self.model
        self.config['base_url'] = self.base_url
        
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
        self._update_endpoints()

    def list_models(self):
        """Fetches available models from the provider."""
        try:
            req = urllib.request.Request(self.tags_endpoint)
            if self.provider == "openai" and self.api_key:
                 req.add_header("Authorization", f"Bearer {self.api_key}")

            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.load(response)
                
                if self.provider == "ollama":
                    return [m['name'] for m in data.get('models', [])]
                else:
                    return [m['id'] for m in data.get('data', [])]
        except Exception as e:
            return [f"Error fetching models: {e}"]

    def chat(self, user_input, history=[]):
        """
        Sends message to LLM. Returns (text_response, tool_call_dict).
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_input}]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"} 
        }

        try:
            req = urllib.request.Request(
                self.chat_endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.load(response)
                content = result['choices'][0]['message']['content']
                
                try:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        data = json.loads(json_str)
                        if "tool" in data and "args" in data:
                            return None, data
                    return content, None 
                except:
                    return content, None
                    
        except urllib.error.URLError as e:
             return f"Connection Error ({self.provider}): {e.reason}. Is the server running?", None
        except Exception as e:
            return f"Error contacting LLM: {e}", None
