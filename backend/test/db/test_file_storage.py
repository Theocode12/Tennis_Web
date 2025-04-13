# test/db/test_file_storage.py  (Create this new file)

import unittest
import tempfile
import shutil
from pathlib import Path

# Assuming BackendFileStorage is accessible, adjust the import path if needed
# Example: from db.file_storage import BackendFileStorage
# Or if running from the root directory:
from db.file_storage import BackendFileStorage

class TestBackendFileStorage(unittest.TestCase):
    """Test suite for the BackendFileStorage class."""

    def setUp(self):
        """Set up a temporary directory before each test."""
        # Create a temporary directory that will be automatically cleaned up
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir_obj.name)
        # print(f"Created temporary directory: {self.temp_dir_path}") # For debugging

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        # The TemporaryDirectory object handles cleanup automatically when it goes out of scope
        # or when its cleanup() method is called (which happens implicitly here).
        # print(f"Cleaning up temporary directory: {self.temp_dir_path}") # For debugging
        pass # No explicit action needed due to TemporaryDirectory

    def test_initialization_creates_directory(self):
        """Test that the base directory is created on initialization if it doesn't exist."""
        test_base_path = self.temp_dir_path / "test_data" / "games"
        self.assertFalse(test_base_path.exists(), "Precondition: Test directory should not exist yet.")

        storage = BackendFileStorage(base_path=str(test_base_path))

        self.assertTrue(test_base_path.exists(), "Directory should be created by __init__.")
        self.assertTrue(test_base_path.is_dir(), "Created path should be a directory.")
        self.assertEqual(storage.base_path, test_base_path)
        self.assertEqual(storage.file_extension, ".json") # Default extension

    def test_initialization_with_existing_directory(self):
        """Test that initialization works correctly if the base directory already exists."""
        test_base_path = self.temp_dir_path / "existing_data"
        test_base_path.mkdir(parents=True, exist_ok=True) # Create it beforehand
        self.assertTrue(test_base_path.exists(), "Precondition: Test directory should exist.")

        # Should not raise an error due to exist_ok=True in mkdir
        storage = BackendFileStorage(base_path=str(test_base_path))

        self.assertTrue(test_base_path.exists(), "Directory should still exist.")
        self.assertTrue(test_base_path.is_dir(), "Path should still be a directory.")
        self.assertEqual(storage.base_path, test_base_path)

    def test_initialization_custom_extension(self):
        """Test initialization with a custom file extension."""
        test_base_path = self.temp_dir_path / "custom_ext_data"
        custom_ext = ".data"

        storage = BackendFileStorage(base_path=str(test_base_path), file_extension=custom_ext)

        self.assertTrue(test_base_path.exists(), "Directory should be created.")
        self.assertEqual(storage.base_path, test_base_path)
        self.assertEqual(storage.file_extension, custom_ext)

    def test_get_game_path_default_settings(self):
        """Test get_game_path with default base path and extension."""
        # Use a path relative to the temp dir for the default base
        default_base = self.temp_dir_path / "data" / "games"
        storage = BackendFileStorage(base_path=str(default_base))
        game_id = "game123"

        expected_path = default_base / f"{game_id}.json"
        actual_path = storage.get_game_path(game_id)

        self.assertIsInstance(actual_path, Path, "Should return a Path object.")
        self.assertEqual(actual_path, expected_path, "Generated path does not match expected path.")

    def test_get_game_path_custom_settings(self):
        """Test get_game_path with custom base path and extension."""
        custom_base = self.temp_dir_path / "my_games"
        custom_ext = ".gamedata"
        storage = BackendFileStorage(base_path=str(custom_base), file_extension=custom_ext)
        game_id = "alpha_beta"

        expected_path = custom_base / f"{game_id}{custom_ext}"
        actual_path = storage.get_game_path(game_id)

        self.assertIsInstance(actual_path, Path, "Should return a Path object.")
        self.assertEqual(actual_path, expected_path, "Generated path with custom settings does not match.")

    def test_get_game_path_different_ids(self):
        """Test get_game_path generates distinct paths for different game IDs."""
        base_path = self.temp_dir_path / "multi_game_data"
        storage = BackendFileStorage(base_path=str(base_path))
        game_id1 = "first_game"
        game_id2 = "second_game"

        path1 = storage.get_game_path(game_id1)
        path2 = storage.get_game_path(game_id2)

        self.assertNotEqual(path1, path2, "Paths for different game IDs should be different.")
        self.assertEqual(path1, base_path / f"{game_id1}.json")
        self.assertEqual(path2, base_path / f"{game_id2}.json")
