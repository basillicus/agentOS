import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import tempfile

# Add the project root to the path to import modules
project_root = os.path.join(os.path.dirname(__file__), '../../agentOS')
sys.path.insert(0, project_root)

from src.skills.memory.manager import MemorySkill
from src.core.schemas import Note, HistoryItem, ActionResponse


class TestMemorySkill(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.memory_skill = MemorySkill(db_path=self.temp_db.name)

    def tearDown(self):
        # Clean up the temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_sanitize_command_removes_sensitive_data(self):
        """Test that sensitive commands are sanitized."""
        test_cases = [
            ("export API_KEY=12345", "export API_KEY=***REDACTED***"),
            ("export SECRET_TOKEN=mytoken", "export SECRET_TOKEN=***REDACTED***"),
            ("aws --secret-access-key mykey", "aws --secret-access-key ***REDACTED***"),
            ("echo password=12345", "echo password=***REDACTED***"),
            ("normal command", "normal command"),  # Should remain unchanged
        ]
        
        for input_cmd, expected in test_cases:
            with self.subTest(input_cmd=input_cmd):
                result = self.memory_skill.sanitize_command(input_cmd)
                self.assertIn(expected.split('=')[0], result)  # Key should remain
                if '=' in expected:
                    self.assertIn("***REDACTED***", result)  # Value should be redacted

    def test_add_and_get_notes(self):
        """Test adding and retrieving notes."""
        # Add a note
        result = self.memory_skill.add_note("Test note content", ["test", "important"])
        self.assertTrue(result.success)
        
        # Retrieve notes
        notes = self.memory_skill.get_notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].content, "Test note content")
        self.assertIn("test", notes[0].tags)
        self.assertIn("important", notes[0].tags)

    def test_get_notes_by_tag(self):
        """Test filtering notes by tag."""
        # Add notes with different tags
        self.memory_skill.add_note("Note 1", ["work"])
        self.memory_skill.add_note("Note 2", ["personal"])
        self.memory_skill.add_note("Note 3", ["work", "urgent"])
        
        # Filter by tag
        work_notes = self.memory_skill.get_notes("work")
        self.assertEqual(len(work_notes), 2)
        for note in work_notes:
            self.assertIn("work", note.tags)

    @patch('builtins.open', new_callable=mock_open, read_data='command1\necho secret=password123\ncommand3')
    @patch('os.path.exists', return_value=True)
    def test_ingest_shell_history(self, mock_exists, mock_file):
        """Test ingesting shell history with sanitization."""
        result = self.memory_skill.ingest_shell_history()
        self.assertTrue(result.success)
        # Verify that sanitized commands were added to history

    def test_scrub_history(self):
        """Test scrubbing history by pattern."""
        # Add some test history items
        self.memory_skill.add_history("test command one")
        self.memory_skill.add_history("test command two")
        self.memory_skill.add_history("other command")
        
        # Scrub items matching "test"
        result = self.memory_skill.scrub_history("test")
        self.assertTrue(result.success)
        
        # Verify that only non-matching items remain
        remaining = self.memory_skill.search_history("")
        self.assertEqual(len(remaining), 1)
        self.assertNotIn("test", remaining[0].command)

    def test_search_history(self):
        """Test searching history."""
        # Add some test history items
        self.memory_skill.add_history("install package manager")
        self.memory_skill.add_history("update system packages")
        self.memory_skill.add_history("configure firewall")
        
        # Search for "package"
        results = self.memory_skill.search_history("package")
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn("package", result.command)


if __name__ == '__main__':
    unittest.main()