import unittest
from unittest.mock import patch, MagicMock
import asyncio
import sys
import os
from typing import List
import logfire

# Add the project root to the path to import modules
project_root = os.path.join(os.path.dirname(__file__), '../../agentOS')
sys.path.insert(0, project_root)

from src.core.engine import get_agent
from src.core.dependencies import AgentDeps
from src.skills.disk.cleaner import DiskSkill
from src.skills.memory.manager import MemorySkill
from src.skills.system.tools import SystemSkill
from src.core.schemas import CacheItem, ActionResponse, Note, HistoryItem


class TestAgentLogfireEvaluation(unittest.TestCase):
    """
    Evaluation tests for the AgentOS agent using Logfire for observability.
    These tests evaluate the agent's ability to handle various user requests
    and properly utilize its tools, with logging for analysis.
    """
    
    def setUp(self):
        # Configure logfire for testing
        logfire.configure(send_to_logfire=False)  # Disable sending to logfire servers during tests
        
        # Create mock skills for testing
        self.disk_skill = DiskSkill()
        self.memory_skill = MemorySkill()
        self.system_skill = SystemSkill()
        self.deps = AgentDeps(self.disk_skill, self.memory_skill, self.system_skill)

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    @logfire.instrument("Testing agent disk cache query")
    def test_agent_disk_cache_query(self, mock_run, mock_exists):
        """Evaluate the agent's response to a disk cache query with logfire instrumentation."""
        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if 'du -sk' in cmd:
                mock_result.stdout = "1024"
                mock_result.stderr = ""
                mock_result.returncode = 0
            else:
                mock_result.stdout = "success"
                mock_result.stderr = ""
                mock_result.returncode = 0
            return mock_result
        
        mock_run.side_effect = mock_subprocess_side_effect
        
        with logfire.span("Getting disk caches"):
            caches = self.disk_skill.get_caches()
            
        self.assertGreater(len(caches), 0)
        for cache in caches:
            with logfire.span("Validating cache item", cache_id=cache.id):
                self.assertIsInstance(cache, CacheItem)
                logfire.info("Validated cache item", cache_name=cache.name, size=cache.size_human)

    @patch('os.path.exists', return_value=True)
    @patch('sqlite3.connect')
    @logfire.instrument("Testing agent memory operations")
    def test_agent_memory_operations(self, mock_connect, mock_exists):
        """Evaluate the agent's memory operations with logfire instrumentation."""
        # Mock the database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [0]  # For count queries
        mock_cursor.fetchall.return_value = []   # For select queries
        mock_connect.return_value = mock_conn
        
        with logfire.span("Adding note to memory"):
            result = self.memory_skill.add_note("Test evaluation note", ["evaluation", "test"])
            
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)
        
        with logfire.span("Retrieving notes from memory"):
            notes = self.memory_skill.get_notes()
            
        self.assertIsInstance(notes, list)
        logfire.info("Memory operations completed", note_count=len(notes))

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    @logfire.instrument("Testing agent system maintenance query")
    def test_agent_system_maintenance_query(self, mock_run, mock_exists):
        """Evaluate the agent's response to system maintenance queries with logfire instrumentation."""
        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if 'du -sh' in cmd:
                mock_result.stdout = "500M"
                mock_result.stderr = ""
                mock_result.returncode = 0
            elif 'journalctl --disk-usage' in cmd:
                mock_result.stdout = "Journal files are using 1.5G"
                mock_result.stderr = "Archived journals taking up space: 1.5G"
                mock_result.returncode = 0
            else:
                mock_result.stdout = "success"
                mock_result.stderr = ""
                mock_result.returncode = 0
            return mock_result
        
        mock_run.side_effect = mock_subprocess_side_effect
        
        with logfire.span("Getting system status"):
            status = self.system_skill.get_status()
            
        self.assertIn('trash', status)
        self.assertIn('apt', status)
        self.assertIn('journal', status)
        logfire.info("System status retrieved", status=status)

    @logfire.instrument("Testing agent tool registration")
    def test_agent_tool_registration(self):
        """Evaluate that the agent has all expected tools registered with logfire instrumentation."""
        with logfire.span("Creating agent"):
            # Create the agent
            agent = get_agent()
        
        # While we can't directly inspect the tools in pydantic-ai,
        # we can verify that the agent factory function works
        self.assertIsNotNone(agent)
        
        # Test that dependencies are properly structured
        self.assertIsInstance(self.deps, AgentDeps)
        self.assertIsInstance(self.deps.disk, DiskSkill)
        self.assertIsInstance(self.deps.memory, MemorySkill)
        self.assertIsInstance(self.deps.system, SystemSkill)
        
        logfire.info("Agent dependencies validated")

    @patch('os.path.exists', return_value=True)
    @patch('subprocess.run')
    @logfire.instrument("Testing agent large files scan")
    def test_agent_large_files_scan(self, mock_run, mock_exists):
        """Evaluate the agent's ability to scan for large files with logfire instrumentation."""
        def mock_subprocess_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if 'find ~ -type f' in cmd:
                mock_result.stdout = "1.2G\t/home/user/huge_file.zip\n500M\t/home/user/large_doc.pdf"
                mock_result.stderr = ""
                mock_result.returncode = 0
            else:
                mock_result.stdout = "success"
                mock_result.stderr = ""
                mock_result.returncode = 0
            return mock_result
        
        mock_run.side_effect = mock_subprocess_side_effect
        
        with logfire.span("Scanning for large files", threshold="100M"):
            result = self.disk_skill.list_large_files("100M")
            
        self.assertIsNotNone(result)
        self.assertGreater(len(result.files), 0)
        self.assertEqual(result.threshold_used, "100M")
        
        logfire.info("Large files scan completed", file_count=len(result.files))

    @patch('os.path.exists', return_value=True)
    @patch('sqlite3.connect')
    @logfire.instrument("Testing agent history operations")
    def test_agent_history_operations(self, mock_connect, mock_exists):
        """Evaluate the agent's history operations with logfire instrumentation."""
        # Mock the database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [0]  # For count queries
        mock_cursor.fetchall.return_value = [(1, "ls -la", "~", "2023-01-01T00:00:00", None)]  # For select queries
        mock_connect.return_value = mock_conn
        
        with logfire.span("Adding command to history"):
            result = self.memory_skill.add_history("test command", "/home/user")
            
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)
        
        with logfire.span("Searching history", search_term="test"):
            history_items = self.memory_skill.search_history("test")
            
        self.assertIsInstance(history_items, List)
        if history_items:
            self.assertIsInstance(history_items[0], HistoryItem)
        
        logfire.info("History operations completed", history_count=len(history_items))

    @logfire.instrument("Testing agent response quality metrics")
    def test_agent_response_quality_metrics(self):
        """
        Evaluate the quality of agent responses based on various criteria:
        - Completeness of information
        - Accuracy of tool usage
        - Proper error handling
        """
        # This test would typically involve running the agent with various prompts
        # and evaluating the responses. For now, we verify that the components
        # that would be used by the agent are functioning properly.
        
        # Verify that all skills have their required methods
        disk_methods = ['get_caches', 'clean_cache', 'list_large_files', 'explore_folder']
        for method in disk_methods:
            with logfire.span("Checking disk skill method", method=method):
                self.assertTrue(hasattr(self.disk_skill, method))
        
        memory_methods = ['add_note', 'get_notes', 'search_history', 'ingest_shell_history', 'scrub_history']
        for method in memory_methods:
            with logfire.span("Checking memory skill method", method=method):
                self.assertTrue(hasattr(self.memory_skill, method))
        
        system_methods = ['docker_prune', 'vacuum_logs', 'apt_clean', 'empty_trash', 'get_status']
        for method in system_methods:
            with logfire.span("Checking system skill method", method=method):
                self.assertTrue(hasattr(self.system_skill, method))
                
        logfire.info("All skill methods validated", disk_methods=len(disk_methods), 
                    memory_methods=len(memory_methods), system_methods=len(system_methods))


class AgentBenchmarkWithLogfireTests(unittest.TestCase):
    """
    Benchmark tests to evaluate agent performance with logfire instrumentation.
    """
    
    def setUp(self):
        # Configure logfire for testing
        logfire.configure(send_to_logfire=False)  # Disable sending to logfire servers during tests
        
        self.disk_skill = DiskSkill()
        self.memory_skill = MemorySkill()
        self.system_skill = SystemSkill()
        self.deps = AgentDeps(self.disk_skill, self.memory_skill, self.system_skill)

    @unittest.skip("Performance test - enable when needed")
    @logfire.instrument("Benchmarking agent response time")
    def test_agent_response_time(self):
        """
        Benchmark the agent's response time for various operations with logfire instrumentation.
        This test is skipped by default to avoid slowing down regular test runs.
        """
        import time
        
        with logfire.span("Measuring cache retrieval time"):
            start_time = time.time()
            caches = self.disk_skill.get_caches()
            end_time = time.time()
        
        response_time = end_time - start_time
        
        # Log the response time for analysis
        logfire.metric('response_time_seconds', response_time, 
                      {'operation': 'get_caches', 'cache_count': len(caches)})
        
        # Assert that the operation completes within a reasonable time
        self.assertLess(response_time, 5.0)  # Less than 5 seconds
        logfire.info("Response time benchmark completed", response_time=response_time)


if __name__ == '__main__':
    unittest.main()