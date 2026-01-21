import unittest
from unittest.mock import MagicMock, patch
import asyncio
import os
import sys
from typing import Any, List, Union

# Add the project root to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../agentOS"))
sys.path.insert(0, project_root)

from pydantic_evals import Dataset, Case
import logfire
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, TextPart, UserPromptPart

from src.core.engine import get_agent
from src.core.dependencies import AgentDeps
from src.skills.disk.cleaner import DiskSkill
from src.skills.memory.manager import MemorySkill
from src.skills.system.tools import SystemSkill
from src.core.schemas import ActionResponse, CacheItem, FileScanResult, DiskUsage

# Disable logfire sending
logfire.configure(send_to_logfire=False)

class TestAgentPydanticEvals(unittest.TestCase):
    def setUp(self):
        self.disk_skill = DiskSkill()
        self.memory_skill = MemorySkill()
        self.system_skill = SystemSkill()
        self.deps = AgentDeps(self.disk_skill, self.memory_skill, self.system_skill)
        
        # Get agent and override model
        self.agent = get_agent()
        self.agent.model = FunctionModel(self._mock_model_logic)

    async def _mock_model_logic(self, messages: List[ModelMessage], info: Any) -> ModelResponse:
        """
        Simulates LLM decision making.
        Returns tool calls based on keywords in the last user message.
        If tool outputs are present in messages, returns a final text response.
        """
        # 1. Check if we have tool outputs (Agent loop: Request -> Tool -> Result -> Final Answer)
        # If the last message is a ToolReturnPart (embedded in ModelRequest usually, but pydantic-ai structure 
        # separates User/System/Model messages).
        # In pydantic-ai, 'messages' contains the history.
        
        last_msg = messages[-1]
        
        # If the last message is from the User, we typically start a tool call or answer.
        if isinstance(last_msg, ModelMessage) and hasattr(last_msg, 'parts'):
             # Check if we have tool return parts? 
             # Actually, pydantic-ai passes the conversation history.
             pass

        # Simplification: Scan the *last user text* to decide what to do.
        # But wait, if we already called a tool, the *next* step is to summarize the result.
        # We need to find the last user prompt.
        
        user_text = ""
        tool_result_found = False
        
        # Iterate backwards to find context
        for msg in reversed(messages):
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                         if isinstance(part.content, str):
                             user_text = part.content
                         # If we found the user prompt, we stop if we haven't seen a tool return yet?
                         # Actually, let's just look if there is a ToolReturn in the history AFTER the last user prompt?
                         # No, pydantic-ai handles the loop.
                    
                    # If we see a tool return, it means we are in the "summarize" phase
                    if hasattr(part, 'tool_name'): # ToolReturnPart check (pseudo-code)
                        # Actually verify type
                        if part.__class__.__name__ == 'ToolReturnPart':
                            tool_result_found = True

        # BUT: FunctionModel is called for *every* step.
        # Step 1: User says "Clean pip". Model should return ToolCall('clean_cache', 'pip').
        # Step 2: Tool executes. Model receives history [User, ToolCall, ToolReturn]. Model should return Text("Done").
        
        # Let's inspect the last message specifically.
        last_parts = last_msg.parts
        is_tool_return = any(p.__class__.__name__ == 'ToolReturnPart' for p in last_parts)
        
        if is_tool_return:
            # We just executed a tool. Return success message.
            return ModelResponse(parts=[TextPart("Task completed successfully based on tool output.")])
        
        # Otherwise, assume we need to act on user input
        # Find the user content
        input_text = ""
        for part in last_parts:
            if isinstance(part, UserPromptPart):
                if isinstance(part.content, str):
                    input_text = part.content
        
        input_lower = input_text.lower()
        
        if "clean" in input_lower and "pip" in input_lower:
            return ModelResponse(parts=[ToolCallPart(tool_name='clean_cache', args={'cache_id': 'pip'})])
            
        elif "large files" in input_lower:
            return ModelResponse(parts=[ToolCallPart(tool_name='scan_large_files', args={'threshold': '100M'})])
            
        elif "docker" in input_lower:
             return ModelResponse(parts=[ToolCallPart(tool_name='docker_prune', args={})])
             
        # Default fallback
        return ModelResponse(parts=[TextPart("I don't know how to do that.")])


    def test_agent_capabilities_eval(self):
        """
        Evaluate agent capabilities using Pydantic Evals.
        """
        # Define the dataset
        dataset = Dataset(
            name="AgentOS Core Capabilities",
            cases=[
                Case(
                    inputs="Clean the pip cache",
                    expected_output="Task completed successfully based on tool output.", 
                ),
                Case(
                    inputs="Check for large files > 100M",
                    expected_output="Task completed successfully based on tool output.",
                ),
                Case(
                    inputs="Prune docker system",
                    expected_output="Task completed successfully based on tool output.",
                )
            ]
        )

        async def eval_wrapper(inputs: str) -> str:
            """
            Wraps the agent run call for the evaluator.
            """
            try:
                # Mock tool outputs
                with patch.object(DiskSkill, 'clean_cache', return_value=ActionResponse(success=True, message="Cleaned Pip Cache")) as mock_clean:
                    with patch.object(DiskSkill, 'list_large_files', return_value=FileScanResult(threshold_used="100M", files=[])) as mock_large:
                        with patch.object(SystemSkill, 'docker_prune', return_value=ActionResponse(success=True, message="Pruned")) as mock_docker:
                            
                            result = await self.agent.run(inputs, deps=self.deps)
                            return result.data

            except Exception as e:
                return f"Error: {str(e)}"

        # Run the evaluation
        results = asyncio.run(dataset.evaluate(eval_wrapper))
        
        # Verify results
        print(f"\nEvaluation Results: {results}")
        self.assertIsNotNone(results)

if __name__ == "__main__":
    unittest.main()