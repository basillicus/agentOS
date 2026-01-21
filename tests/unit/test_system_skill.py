import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to the path to import modules
project_root = os.path.join(os.path.dirname(__file__), '../../agentOS')
sys.path.insert(0, project_root)

from src.skills.system.tools import SystemSkill
from src.core.schemas import ActionResponse


class TestSystemSkill(unittest.TestCase):
    def setUp(self):
        self.system_skill = SystemSkill()

    @patch('shutil.which', return_value='/usr/bin/docker')
    @patch('subprocess.run')
    def test_docker_prune_success(self, mock_run, mock_which):
        """Test docker prune command succeeds."""
        # Mock subprocess to return success
        mock_result = MagicMock()
        mock_result.stdout = "Total reclaimed space: 1.23GB"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.system_skill.docker_prune()
        
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)
        self.assertIn("Docker system pruned", result.message)

    @patch('shutil.which', return_value=None)
    def test_docker_not_found(self, mock_which):
        """Test docker command when docker is not installed."""
        result = self.system_skill.docker_prune()
        
        self.assertIsInstance(result, ActionResponse)
        self.assertFalse(result.success)
        self.assertIn("Docker not found", result.message)

    @patch('subprocess.run')
    def test_vacuum_logs_success(self, mock_run):
        """Test vacuuming logs succeeds."""
        # Mock subprocess to return success
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Vacuuming done, freed 100.0M of archived journals"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.system_skill.vacuum_logs()
        
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)
        self.assertIn("Logs vacuumed", result.message)

    @patch('subprocess.run')
    def test_empty_trash_success(self, mock_run):
        """Test emptying trash succeeds."""
        with patch('os.path.exists', return_value=True):
            with patch('shutil.rmtree'):
                with patch('os.makedirs'):
                    result = self.system_skill.empty_trash()
                    
                    self.assertIsInstance(result, ActionResponse)
                    self.assertTrue(result.success)
                    self.assertIn("Trash emptied", result.message)

    @patch('os.path.exists', return_value=False)
    def test_empty_trash_already_empty(self, mock_exists):
        """Test emptying trash when it's already empty."""
        result = self.system_skill.empty_trash()
        
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)
        self.assertIn("Trash is already empty", result.message)

    @patch('subprocess.run')
    def test_get_status(self, mock_run):
        """Test getting system status."""
        # Mock the du command for trash and apt
        def mock_subprocess_run(cmd, **kwargs):
            mock_result = MagicMock()
            if 'Trash' in cmd:
                mock_result.stdout = "500M"
                mock_result.stderr = ""
                mock_result.returncode = 0
            elif 'apt' in cmd:
                mock_result.stdout = "2.1G"
                mock_result.stderr = ""
                mock_result.returncode = 0
            elif 'journalctl' in cmd:
                mock_result.stdout = "Journal files are using 1.5G (archived: 1.0G, active: 500.0M)"
                mock_result.stderr = "Archived and active journals taking up space: 1.5G"
                mock_result.returncode = 0
            return mock_result
        
        mock_run.side_effect = mock_subprocess_run
        
        status = self.system_skill.get_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('trash', status)
        self.assertIn('apt', status)
        self.assertIn('journal', status)


if __name__ == '__main__':
    unittest.main()