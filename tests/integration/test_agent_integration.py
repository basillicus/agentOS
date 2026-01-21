import unittest
from unittest.mock import patch, MagicMock
import asyncio
import sys
import os

# Add the project root to the path to import modules
project_root = os.path.join(os.path.dirname(__file__), '../../agentOS')
sys.path.insert(0, project_root)

from src.core.engine import get_agent
from src.core.dependencies import AgentDeps
from src.skills.disk.cleaner import DiskSkill
from src.skills.memory.manager import MemorySkill
from src.skills.system.tools import SystemSkill
from src.core.schemas import CacheItem, ActionResponse


class TestAgentIntegration(unittest.TestCase):
    def setUp(self):
        # Create mock skills for testing
        self.disk_skill = DiskSkill()
        self.memory_skill = MemorySkill()
        self.system_skill = SystemSkill()
        self.deps = AgentDeps(self.disk_skill, self.memory_skill, self.system_skill)

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    def test_agent_with_mock_model(self, mock_run, mock_exists):
        """Test the agent with mocked dependencies and model."""
        # Mock subprocess calls to return predictable results
        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if 'du -sk' in cmd:
                mock_result.stdout = "1024"
                mock_result.stderr = ""
                mock_result.returncode = 0
            elif 'find ~ -type f' in cmd:
                mock_result.stdout = "500M\t/home/user/test_file.txt"
                mock_result.stderr = ""
                mock_result.returncode = 0
            else:
                mock_result.stdout = "success"
                mock_result.stderr = ""
                mock_result.returncode = 0
            return mock_result
        
        mock_run.side_effect = mock_subprocess_side_effect
        
        # Create the agent
        agent = get_agent()
        
        # Verify that the agent has the expected tools registered
        self.assertIsNotNone(agent)
        # Note: We can't directly access the tools list in pydantic-ai, 
        # but we can test that the agent was created successfully
        
        # Test that dependencies are properly structured
        self.assertIsInstance(self.deps.disk, DiskSkill)
        self.assertIsInstance(self.deps.memory, MemorySkill)
        self.assertIsInstance(self.deps.system, SystemSkill)

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    def test_disk_tools_integration(self, mock_run, mock_exists):
        """Test that disk tools work correctly with the agent dependencies."""
        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if 'du -sk' in cmd:
                mock_result.stdout = "2048"
                mock_result.stderr = ""
                mock_result.returncode = 0
            elif 'find ~ -type f' in cmd:
                mock_result.stdout = "500M\t/home/user/test_file.txt\n300M\t/home/user/another_file.txt"
                mock_result.stderr = ""
                mock_result.returncode = 0
            else:
                mock_result.stdout = "cleaned"
                mock_result.stderr = ""
                mock_result.returncode = 0
            return mock_result
        
        mock_run.side_effect = mock_subprocess_side_effect
        
        # Test the disk skill through dependencies
        caches = self.deps.disk.get_caches()
        
        # Verify that we get CacheItem objects
        if caches:
            self.assertIsInstance(caches[0], CacheItem)
            self.assertGreater(caches[0].size_bytes, 0)

        # Test large file scanning
        large_files_result = self.deps.disk.list_large_files("100M")
        self.assertIsNotNone(large_files_result)
        self.assertEqual(large_files_result.threshold_used, "100M")

    @patch('os.path.exists', return_value=True)
    @patch('sqlite3.connect')
    def test_memory_tools_integration(self, mock_connect, mock_exists):
        """Test that memory tools work correctly with the agent dependencies."""
        # Mock the database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock cursor fetchone and fetchall methods
        mock_cursor.fetchone.return_value = [0]  # For count queries
        mock_cursor.fetchall.return_value = []   # For select queries
        
        mock_connect.return_value = mock_conn
        
        # Test adding a note
        result = self.deps.memory.add_note("Test note", ["test", "integration"])
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)

        # Test getting notes
        notes = self.deps.memory.get_notes()
        self.assertIsInstance(notes, list)

    def test_dependencies_structure(self):
        """Test that the dependencies are structured correctly."""
        self.assertIsInstance(self.deps, AgentDeps)
        self.assertIsInstance(self.deps.disk, DiskSkill)
        self.assertIsInstance(self.deps.memory, MemorySkill)
        self.assertIsInstance(self.deps.system, SystemSkill)


if __name__ == '__main__':
    unittest.main()