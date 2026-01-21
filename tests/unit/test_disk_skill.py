import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from typing import List

# Add the project root to the path to import modules
project_root = os.path.join(os.path.dirname(__file__), '../../agentOS')
sys.path.insert(0, project_root)

from src.skills.disk.cleaner import DiskSkill
from src.core.schemas import CacheItem, ActionResponse, DiskUsage, FileScanResult


class TestDiskSkill(unittest.TestCase):
    def setUp(self):
        self.disk_skill = DiskSkill()

    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_get_caches(self, mock_run, mock_exists):
        """Test that get_caches returns properly formatted CacheItems."""
        # Mock the subprocess call to return a size
        mock_result = MagicMock()
        mock_result.stdout = "1024"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Mock path existence
        mock_exists.return_value = True
        
        caches = self.disk_skill.get_caches()
        
        # Verify that we get CacheItem objects
        self.assertIsInstance(caches, list)
        if caches:  # If there are caches defined
            self.assertIsInstance(caches[0], CacheItem)
            self.assertGreaterEqual(len(caches[0].id), 1)  # Should have an ID
            self.assertGreaterEqual(len(caches[0].name), 1)  # Should have a name

    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_clean_cache_success(self, mock_run, mock_exists):
        """Test cleaning a cache successfully."""
        # Mock subprocess to simulate successful command
        mock_result = MagicMock()
        mock_result.stdout = "Cleaned successfully"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Mock path existence
        mock_exists.return_value = True
        
        result = self.disk_skill.clean_cache('pip')
        
        self.assertIsInstance(result, ActionResponse)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.message)

    @patch('os.path.exists')
    def test_clean_cache_invalid_id(self, mock_exists):
        """Test cleaning a cache with invalid ID."""
        mock_exists.return_value = True
        
        result = self.disk_skill.clean_cache('invalid_cache_id')
        
        self.assertIsInstance(result, ActionResponse)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid ID")

    @patch('subprocess.run')
    def test_list_large_files(self, mock_run):
        """Test listing large files."""
        # Mock subprocess to return sample output
        mock_result = MagicMock()
        mock_result.stdout = "500M\t/home/user/large_file.txt\n200M\t/home/user/medium_file.txt"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.disk_skill.list_large_files('100M')
        
        self.assertIsInstance(result, FileScanResult)
        self.assertEqual(result.threshold_used, '100M')

    @patch('os.path.exists')
    @patch('os.scandir')
    def test_explore_folder(self, mock_scandir, mock_exists):
        """Test exploring a folder."""
        # Mock directory entry
        mock_entry = MagicMock()
        mock_entry.is_dir.return_value = True
        mock_entry.name = 'test_dir'
        mock_entry.path = '/home/user/test_dir'
        
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = [mock_entry]
        mock_context_manager.__exit__.return_value = None
        mock_scandir.return_value = mock_context_manager
        
        mock_exists.return_value = True
        
        result = self.disk_skill.explore_folder('~')
        
        if result:  # If there are results
            self.assertIsInstance(result[0], DiskUsage)
            self.assertEqual(result[0].name, 'test_dir')


if __name__ == '__main__':
    unittest.main()