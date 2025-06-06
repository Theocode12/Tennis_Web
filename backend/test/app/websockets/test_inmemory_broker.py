from __future__ import annotations

import asyncio
import unittest
from collections.abc import AsyncIterator
from typing import Any

from app.broker.memory_message_broker import InMemoryMessageBroker


async def consume_messages(
    generator: AsyncIterator[Any], count: int, timeout: float = 1.0
) -> list[Any]:
    """Helper coroutine to consume a specific number of messages."""
    messages = []
    for _ in range(count):
        try:
            # Use asyncio.wait_for to handle timeout on the __anext__ call
            message = await asyncio.wait_for(generator.__anext__(), timeout=timeout)
            messages.append(message)
        except (StopAsyncIteration, asyncio.TimeoutError) as e:
            # Stop if generator ends early or times out
            raise e
    return messages


class TestInMemoryMessageBroker(unittest.IsolatedAsyncioTestCase):
    """Test suite for the InMemoryMessageBroker using unittest."""

    async def asyncSetUp(self):
        """Set up a fresh broker instance before each test."""
        self.broker = InMemoryMessageBroker()
        # Allow internal inspection for specific tests
        self._subscribers_ref = self.broker._subscribers

    async def asyncTearDown(self):
        """Shut down the broker after each test."""
        await self.broker.shutdown()

    async def test_publish_subscribe_single(self):
        """Test basic publish/subscribe for a single subscriber."""
        game_id = "game1"
        channel = "scores"
        message_to_send = {"score": "15-0"}

        subscriber_gen = self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)  # Allow subscription task switch

        publish_count = await self.broker.publish(game_id, channel, message_to_send)
        self.assertEqual(publish_count, 1)

        received_messages = await consume_messages(subscriber_gen, 1, timeout=0.5)

        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0], message_to_send)
        await subscriber_gen.aclose()  # Clean up generator

    async def test_publish_subscribe_multiple_subscribers(self):
        """Test publishing to multiple subscribers on the same channel."""
        game_id = "game2"
        channel = "updates"
        message = {"status": "running"}

        sub1_gen = self.broker.subscribe(game_id, channel)
        sub2_gen = self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)

        publish_count = await self.broker.publish(game_id, channel, message)
        self.assertEqual(publish_count, 2)

        # Consume messages concurrently
        results = await asyncio.gather(
            consume_messages(sub1_gen, 1, timeout=0.5),
            consume_messages(sub2_gen, 1, timeout=0.5),
        )

        self.assertEqual(len(results[0]), 1)
        self.assertEqual(results[0][0], message)
        self.assertEqual(len(results[1]), 1)
        self.assertEqual(results[1][0], message)
        await asyncio.gather(sub1_gen.aclose(), sub2_gen.aclose())  # Cleanup

    async def test_publish_no_subscribers(self):
        """Test publishing to a channel with no subscribers."""
        game_id = "game3"
        channel = "commands"
        message = {"cmd": "start"}

        publish_count = await self.broker.publish(game_id, channel, message)
        self.assertEqual(publish_count, 0)

    async def test_subscribe_multiple_messages(self):
        """Test a single subscriber receiving multiple messages."""
        game_id = "game4"
        channel = "log"
        messages = [{"level": "info", "msg": "one"}, {"level": "warn", "msg": "two"}]

        subscriber_gen = self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)

        count1 = await self.broker.publish(game_id, channel, messages[0])
        count2 = await self.broker.publish(game_id, channel, messages[1])
        self.assertEqual(count1, 1)
        self.assertEqual(count2, 1)

        received = await consume_messages(subscriber_gen, 2, timeout=0.5)

        self.assertEqual(len(received), 2)
        self.assertListEqual(received, messages)  # Use assertListEqual for lists
        await subscriber_gen.aclose()

    async def test_isolation_between_games(self):
        """Test that messages for one game_id don't reach another."""
        game1 = "g_iso1"
        game2 = "g_iso2"
        channel = "data"
        msg1 = {"game": game1}
        msg2 = {"game": game2}

        sub1_gen = self.broker.subscribe(game1, channel)
        sub2_gen = self.broker.subscribe(game2, channel)
        await asyncio.sleep(0.01)

        await self.broker.publish(game1, channel, msg1)
        await self.broker.publish(game2, channel, msg2)

        # Check sub1 receives only msg1
        received1 = await consume_messages(sub1_gen, 1, timeout=0.5)
        self.assertEqual(len(received1), 1)
        self.assertEqual(received1[0], msg1)
        # Check sub1 doesn't receive msg2 shortly after
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(sub1_gen, 1, timeout=0.1)

        # Check sub2 receives only msg2
        received2 = await consume_messages(sub2_gen, 1, timeout=0.5)
        self.assertEqual(len(received2), 1)
        self.assertEqual(received2[0], msg2)
        # Check sub2 doesn't receive msg1 shortly after
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(sub2_gen, 1, timeout=0.1)

        await asyncio.gather(sub1_gen.aclose(), sub2_gen.aclose())

    async def test_isolation_between_channels(self):
        """Test that messages for one channel don't reach another within the same game."""
        game_id = "g_chan_iso"
        channel1 = "chanA"
        channel2 = "chanB"
        msg1 = {"channel": channel1}
        msg2 = {"channel": channel2}

        sub1_gen = self.broker.subscribe(game_id, channel1)
        sub2_gen = self.broker.subscribe(game_id, channel2)
        await asyncio.sleep(0.01)

        await self.broker.publish(game_id, channel1, msg1)
        await self.broker.publish(game_id, channel2, msg2)

        # Check sub1 receives only msg1
        received1 = await consume_messages(sub1_gen, 1, timeout=0.5)
        self.assertEqual(len(received1), 1)
        self.assertEqual(received1[0], msg1)
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(sub1_gen, 1, timeout=0.1)

        # Check sub2 receives only msg2
        received2 = await consume_messages(sub2_gen, 1, timeout=0.5)
        self.assertEqual(len(received2), 1)
        self.assertEqual(received2[0], msg2)
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(sub2_gen, 1, timeout=0.1)

        await asyncio.gather(sub1_gen.aclose(), sub2_gen.aclose())

    async def test_broadcast(self):
        """Test broadcasting to a specific channel across all games."""
        game1 = "bcast_g1"
        game2 = "bcast_g2"
        channel_x = "alert"
        channel_y = "status"  # Should not receive broadcast
        message = {"broadcast": "important"}

        sub_g1_x = self.broker.subscribe(game1, channel_x)
        sub_g2_x = self.broker.subscribe(game2, channel_x)
        sub_g1_y = self.broker.subscribe(game1, channel_y)
        await asyncio.sleep(0.01)

        broadcast_count = await self.broker.broadcast(channel_x, message)
        self.assertEqual(broadcast_count, 2)  # Only subscribers to channel_x

        # Check recipients
        received_g1_x = await consume_messages(sub_g1_x, 1, timeout=0.5)
        received_g2_x = await consume_messages(sub_g2_x, 1, timeout=0.5)

        self.assertEqual(len(received_g1_x), 1)
        self.assertEqual(received_g1_x[0], message)
        self.assertEqual(len(received_g2_x), 1)
        self.assertEqual(received_g2_x[0], message)

        # Check non-recipient
        with self.assertRaises(asyncio.TimeoutError):
            await consume_messages(sub_g1_y, 1, timeout=0.1)

        await asyncio.gather(sub_g1_x.aclose(), sub_g2_x.aclose(), sub_g1_y.aclose())

    async def test_shutdown_stops_subscribers(self):
        """Test that subscribers stop receiving messages after shutdown."""
        game_id = "shutdown_test"
        channel = "data"

        subscriber_gen = self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)

        # Publish one message before shutdown
        await self.broker.publish(game_id, channel, {"before": "shutdown"})
        received_before = await consume_messages(subscriber_gen, 1, timeout=0.5)
        self.assertEqual(len(received_before), 1)

        # Shutdown the broker
        await self.broker.shutdown()

        # Try consuming again, should raise TimeoutError or StopAsyncIteration
        with self.assertRaises((StopAsyncIteration, asyncio.TimeoutError)):
            await consume_messages(subscriber_gen, 1, timeout=0.1)

        # Also test that the generator doesn't yield the None sentinel
        messages_after_shutdown = []
        try:
            # This loop should not run or yield anything other than return silently or raise
            async for msg in subscriber_gen:
                messages_after_shutdown.append(msg)
        except Exception:
            pass  # Might potentially raise errors after shutdown/close
        self.assertListEqual(messages_after_shutdown, [])

    async def test_shutdown_prevents_publish(self):
        """Test that publishing fails (returns 0) after shutdown."""
        game_id = "shutdown_pub"
        channel = "data"

        # Subscribe so the channel exists internally
        self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)

        await self.broker.shutdown()

        publish_count = await self.broker.publish(
            game_id, channel, {"after": "shutdown"}
        )
        self.assertEqual(publish_count, 0)
        # No need to close generator, shutdown handles it

    async def test_unsubscribe_on_generator_exit(self):
        """Test that the subscriber queue is removed when the generator is exited."""
        game_id = "unsub_test"
        channel = "temp"

        subscriber_gen = self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)

        # --- Find the internal queue associated with this subscriber ---
        # This relies on inspecting internal state, acceptable for testing.
        queues_in_broker: set[asyncio.Queue] = self._subscribers_ref[game_id][
            channel
        ]
        self.assertEqual(len(queues_in_broker), 1)

        # Consume one message to advance the generator past initial setup
        await self.broker.publish(game_id, channel, {"msg": 1})
        _ = await consume_messages(subscriber_gen, 1, timeout=0.5)

        # Simulate the consumer stopping (e.g., breaking from async for)
        # by explicitly closing the generator, which triggers its finally block.
        await subscriber_gen.aclose()

        # Allow the cleanup in the finally block to run
        await asyncio.sleep(0.01)

        # Check subscriber queue is removed internally
        # Use the reference captured in asyncSetUp
        self.assertNotIn(
            game_id, self._subscribers_ref
        )  # Game should be gone if channel was last one

        # Verify by publishing again - should reach 0 subscribers
        publish_count = await self.broker.publish(game_id, channel, {"msg": 2})
        self.assertEqual(publish_count, 0)

    async def test_shutdown_sends_sentinel_and_generator_exits(self):
        """Test that shutdown sends None sentinel causing the generator to exit cleanly."""
        game_id = "shutdown_sentinel"
        channel = "signal"

        subscriber_gen = self.broker.subscribe(game_id, channel)
        await asyncio.sleep(0.01)  # Allow subscription to register

        # Start the shutdown process. This will put None in the queue.
        shutdown_task = asyncio.create_task(self.broker.shutdown())

        # The generator's internal loop should receive the None from queue.get(),
        # hit the `if message is None: break` condition, and exit the loop.
        # Calling __anext__ on a generator that has finished its iteration
        # (either normally or via break/return) raises StopAsyncIteration.

        # Wait for the shutdown process to complete fully.
        await shutdown_task

        # Now, attempt to get the next item from the generator.
        # Since it should have received None and exited its loop,
        # this call should immediately raise StopAsyncIteration.
        with self.assertRaises(StopAsyncIteration):
            await subscriber_gen.__anext__()
