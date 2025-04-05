import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from src.store.decorators.store_scores import store_scores  # Import the decorator

# Sample async function to decorate
async def sample_game_function(game_logic, x, y):
    return x + y  # Returns sum of two numbers

class TestStoreScoresDecorator(unittest.IsolatedAsyncioTestCase):
    async def test_decorator_calls_append_score(self):
        """Test that the decorator calls storage.append_score() with correct arguments"""
        
        # Mock storage with AsyncMock
        mock_storage = MagicMock()
        mock_storage.append_score = AsyncMock()
        
        # Mock game_logic object
        mock_game_logic = MagicMock()
        mock_game_logic.config.game_id = "test_game_123"  # Simulated game ID
        mock_score_payload = {"score": [10, 5]}  # Fake score data
        mock_game_logic.generate_score_payload.return_value = mock_score_payload

        # Apply the decorator
        decorated_function = store_scores(mock_storage)(sample_game_function)

        # Call the decorated function
        result = await decorated_function(mock_game_logic, 2, 3)

        # Assertions
        mock_storage.append_score.assert_awaited_once_with("test_game_123", mock_score_payload)  # Check append_score() call
        self.assertEqual(result, 5)  # Ensure return value is unchanged
