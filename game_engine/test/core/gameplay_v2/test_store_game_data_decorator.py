import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from src.store.decorators.store_game_data import store_game_data  # Import the decorator
from src.store.game_data import GameData

# Sample async function to decorate
async def sample_game_function(game_play, x, y):
    return x + y  # Simple return for testing

class TestStoreGameDataDecorator(unittest.IsolatedAsyncioTestCase):
    async def test_decorator_calls_store_game_data(self):
        """Test that the decorator calls storage.store_game_data()"""
        
        # Mock storage with AsyncMock
        mock_storage = MagicMock()
        mock_storage.store_game_data = AsyncMock()
        
        # Mock GameData.from_game_play
        mock_game_data = MagicMock(spec=GameData)
        with patch("src.store.game_data.GameData.from_game_play", return_value=mock_game_data):
            
            # Decorate the function
            decorated_function = store_game_data(mock_storage)(sample_game_function)
            
            # Create a mock game_play object
            mock_game_play = MagicMock()

            # Call the decorated function
            result = await decorated_function(mock_game_play, 2, 3)
            
            # Assert store_game_data() was called with the expected GameData object
            mock_storage.store_game_data.assert_awaited_once_with(mock_game_data)
            
            # Ensure the function still returns correct result
            self.assertEqual(result, 5)

