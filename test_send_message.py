import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import uuid
from main import ChunkDeliveryManager, MessageReassembler
from backend import database


class TestChunkDeliveryManager(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'message_delivery': {
                'max_chunks': 16,
                'chunk_timeout_seconds': 60,
                'max_chunk_retries': 3,
                'inter_chunk_delay_seconds': 2,
                'retry_delay_seconds': 15,
                'max_message_length_bytes': 3200,
                'metadata_overhead_bytes': 50,
                'enable_chunking': True,
                'enable_confirmations': True
            }
        }
        self.manager = ChunkDeliveryManager(self.config)

    def test_should_chunk_message_small(self):
        """Test that small messages don't get chunked."""
        message = "Short message"
        self.assertFalse(self.manager.should_chunk_message(message))

    def test_should_chunk_message_large(self):
        """Test that large messages get chunked."""
        message = "a" * 300  # Larger than 200 - 50 = 150 threshold
        self.assertTrue(self.manager.should_chunk_message(message))

    def test_should_chunk_message_disabled(self):
        """Test chunking disabled."""
        self.manager.enable_chunking = False
        message = "a" * 300
        self.assertFalse(self.manager.should_chunk_message(message))

    def test_split_message_into_chunks_single(self):
        """Test single chunk returned for small message."""
        message = "Short message"
        message_id = str(uuid.uuid4())
        result = self.manager.split_message_into_chunks(message, message_id)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['content'], message)
        self.assertNotIn('message_id', result[0])

    def test_split_message_into_chunks_basic(self):
        """Test basic chunk splitting."""
        message = "a" * 300  # Should create 3 chunks with new conservative limits
        message_id = str(uuid.uuid4())
        chunks = self.manager.split_message_into_chunks(message, message_id)

        self.assertIsNotNone(chunks)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]['message_id'], message_id)
        self.assertEqual(chunks[0]['chunk_number'], 0)
        self.assertEqual(chunks[0]['total_chunks'], 3)
        self.assertEqual(chunks[1]['chunk_number'], 1)
        self.assertEqual(chunks[1]['total_chunks'], 3)
        self.assertEqual(chunks[2]['chunk_number'], 2)
        self.assertEqual(chunks[2]['total_chunks'], 3)

        # Check content - each chunk should be <= 120 bytes
        for chunk in chunks:
            self.assertLessEqual(len(chunk['content']), 120)

    def test_split_message_into_chunks_max_chunks(self):
        """Test max chunks limit."""
        # Create a very long message that would exceed max_chunks
        message = "a" * (150 * 20)  # 3000 chars, would be 20 chunks
        self.manager.max_chunks = 5  # Set low limit
        message_id = str(uuid.uuid4())
        chunks = self.manager.split_message_into_chunks(message, message_id)

        self.assertIsNotNone(chunks)
        self.assertEqual(len(chunks), 5)  # Limited to max_chunks

    @patch('backend.database.mark_chunk_sent')
    @patch('backend.database.increment_chunk_retry_count')
    @patch('backend.database.mark_chunk_failed')
    def test_send_chunk_success(self, mock_failed, mock_retry, mock_sent):
        """Test successful chunk sending."""
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 1,
            'content': 'test content'
        }
        chunk_id = 1
        mock_interface = Mock()
        mock_interface.sendText.return_value = True

        result = self.manager.send_chunk(chunk_data, chunk_id, 'user1', mock_interface, 'sender1')

        self.assertTrue(result)
        mock_interface.sendText.assert_called_once()
        mock_sent.assert_called_once_with(chunk_id)
        mock_retry.assert_not_called()
        mock_failed.assert_not_called()

    @patch('backend.database.mark_chunk_sent')
    @patch('backend.database.increment_chunk_retry_count')
    @patch('backend.database.mark_chunk_failed')
    def test_send_chunk_retry_success(self, mock_failed, mock_retry, mock_sent):
        """Test chunk sending with retry success."""
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 1,
            'content': 'test content'
        }
        chunk_id = 1
        mock_interface = Mock()
        mock_interface.sendText.side_effect = [Exception("Network error"), True]

        result = self.manager.send_chunk(chunk_data, chunk_id, 'user1', mock_interface, 'sender1')

        self.assertTrue(result)
        self.assertEqual(mock_interface.sendText.call_count, 2)
        mock_sent.assert_called_once_with(chunk_id)
        mock_retry.assert_called_once_with(chunk_id)
        mock_failed.assert_not_called()

    @patch('backend.database.mark_chunk_sent')
    @patch('backend.database.increment_chunk_retry_count')
    @patch('backend.database.mark_chunk_failed')
    def test_send_chunk_all_retries_fail(self, mock_failed, mock_retry, mock_sent):
        """Test chunk sending when all retries fail."""
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 1,
            'content': 'test content'
        }
        chunk_id = 1
        mock_interface = Mock()
        mock_interface.sendText.side_effect = Exception("Network error")

        result = self.manager.send_chunk(chunk_data, chunk_id, 'user1', mock_interface, 'sender1')

        self.assertFalse(result)
        self.assertEqual(mock_interface.sendText.call_count, 3)  # max_retries
        mock_sent.assert_not_called()
        mock_retry.assert_called()
        mock_failed.assert_called_once_with(chunk_id)

    def test_send_chunk_too_large(self):
        """Test chunk rejection when too large."""
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 1,
            'content': 'a' * 200  # Will exceed limit when JSON encoded
        }
        chunk_id = 1
        mock_interface = Mock()

        with patch('backend.database.mark_chunk_failed') as mock_failed:
            result = self.manager.send_chunk(chunk_data, chunk_id, 'user1', mock_interface, 'sender1')

        self.assertFalse(result)
        mock_interface.sendText.assert_not_called()
        mock_failed.assert_called_once_with(chunk_id)

    @patch('backend.database.insert_delivery_status')
    @patch('backend.database.insert_message_chunk')
    @patch('backend.database.mark_chunk_sent')
    def test_send_message_chunks_small_message(self, mock_sent, mock_insert_chunk, mock_insert_delivery):
        """Test sending small message (no chunking)."""
        message = "Short message"
        mock_interface = Mock()
        mock_interface.sendText.return_value = True

        with patch.object(self.manager, 'send_single_message') as mock_single:
            mock_single.return_value = 'msg-123'
            result = self.manager.send_message_chunks(message, 'user1', mock_interface, 'sender1', 'receiver1')

        mock_single.assert_called_once()
        self.assertEqual(result, 'msg-123')

    @patch('backend.database.insert_delivery_status')
    @patch('backend.database.insert_message_chunk')
    @patch('backend.database.mark_chunk_sent')
    def test_send_message_chunks_large_message(self, mock_sent, mock_insert_chunk, mock_insert_delivery):
        """Test sending large message with chunking."""
        message = "a" * 300
        mock_interface = Mock()
        mock_interface.sendText.return_value = True

        mock_insert_delivery.return_value = 1
        mock_insert_chunk.side_effect = [1, 2, 3]  # chunk IDs for 3 chunks

        with patch.object(self.manager, 'send_chunk') as mock_send_chunk:
            mock_send_chunk.return_value = True
            result = self.manager.send_message_chunks(message, 'user1', mock_interface, 'sender1', 'receiver1')

        self.assertIsInstance(result, str)  # message_id
        mock_insert_delivery.assert_called_once()
        self.assertEqual(mock_insert_chunk.call_count, 3)
        self.assertEqual(mock_send_chunk.call_count, 3)

    @patch('backend.database.insert_message_chunk')
    @patch('backend.database.mark_chunk_sent')
    def test_send_single_message_success(self, mock_sent, mock_insert_chunk):
        """Test sending single message successfully."""
        message = "Test message"
        mock_interface = Mock()
        mock_interface.sendText.return_value = True

        mock_insert_chunk.return_value = 1

        result = self.manager.send_single_message(message, 'user1', mock_interface, 'sender1', 'receiver1')

        self.assertIsInstance(result, str)  # message_id
        mock_interface.sendText.assert_called_once_with(message, destinationId='user1', wantAck=True)
        mock_sent.assert_called_once_with(1)

    @patch('backend.database.insert_message_chunk')
    @patch('backend.database.mark_chunk_failed')
    @patch('backend.database.increment_chunk_retry_count')
    def test_send_single_message_retry_fail(self, mock_retry, mock_failed, mock_insert_chunk):
        """Test single message sending with retries failing."""
        message = "Test message"
        mock_interface = Mock()
        mock_interface.sendText.side_effect = Exception("Send failed")

        mock_insert_chunk.return_value = 1

        result = self.manager.send_single_message(message, 'user1', mock_interface, 'sender1', 'receiver1')

        self.assertIsInstance(result, str)  # message_id
        self.assertEqual(mock_interface.sendText.call_count, 3)  # max_retries
        mock_failed.assert_called_once_with(1)
        mock_retry.assert_called()


class TestMessageReassembler(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'message_delivery': {
                'enable_confirmations': True
            }
        }
        self.reassembler = MessageReassembler(self.config)

    def test_process_chunk_valid(self):
        """Test processing a valid chunk."""
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 2,
            'content': 'Hello '
        }

        with patch('backend.database.insert_message_chunk') as mock_insert:
            with patch('backend.database.get_message_chunks') as mock_get:
                mock_insert.return_value = 1
                mock_get.return_value = []  # No complete message yet

                result = self.reassembler.process_chunk(chunk_data, 'sender1', 'receiver1', Mock())

        self.assertIsNone(result)  # Message not complete
        mock_insert.assert_called_once()

    def test_process_chunk_invalid(self):
        """Test processing invalid chunk data."""
        chunk_data = {
            'chunk_number': 0,
            'total_chunks': 2
            # Missing message_id, content
        }

        result = self.reassembler.process_chunk(chunk_data, 'sender1', 'receiver1', Mock())
        self.assertIsNone(result)

    def test_process_chunk_json_string(self):
        """Test processing chunk from JSON string."""
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 1,
            'content': 'Complete message'
        }
        json_data = json.dumps(chunk_data)

        with patch('backend.database.insert_message_chunk') as mock_insert:
            with patch('backend.database.get_message_chunks') as mock_get:
                with patch('backend.database.get_delivery_status_for_message') as mock_delivery:
                    with patch('backend.database.complete_message_delivery') as mock_complete:
                        mock_insert.return_value = 1
                        mock_get.return_value = [{
                            'id': 1,
                            'chunk_number': 0,
                            'total_chunks': 1,
                            'content': 'Complete message',
                            'status': 'delivered',
                            'sender_id': 'sender1'
                        }]
                        mock_delivery.return_value = [{'id': 1}]

                        result = self.reassembler.process_chunk(json_data, 'sender1', 'receiver1', Mock())

        self.assertIsNotNone(result)
        self.assertEqual(result['full_message'], 'Complete message')
        mock_complete.assert_called_once()

    def test_check_message_complete(self):
        """Test checking if message is complete."""
        message_id = str(uuid.uuid4())

        with patch('backend.database.get_message_chunks') as mock_get:
            # Not all chunks delivered
            mock_get.return_value = [
                {'chunk_number': 0, 'total_chunks': 2, 'status': 'delivered', 'content': 'Hello '},
                {'chunk_number': 1, 'total_chunks': 2, 'status': 'pending', 'content': 'world'}
            ]

            result = self.reassembler.check_message_complete(message_id, 'receiver1')
            self.assertIsNone(result)

            # All chunks delivered
            mock_get.return_value = [
                {'chunk_number': 0, 'total_chunks': 2, 'status': 'delivered', 'content': 'Hello ', 'sender_id': 'sender1'},
                {'chunk_number': 1, 'total_chunks': 2, 'status': 'delivered', 'content': 'world', 'sender_id': 'sender1'}
            ]

            with patch('backend.database.get_delivery_status_for_message') as mock_delivery:
                with patch('backend.database.complete_message_delivery') as mock_complete:
                    mock_delivery.return_value = [{'id': 1}]

                    result = self.reassembler.check_message_complete(message_id, 'receiver1')

            self.assertIsNotNone(result)
            self.assertEqual(result['full_message'], 'Hello world')
            mock_complete.assert_called_once()

    def test_reassemble_message(self):
        """Test message reassembly."""
        chunks = [
            {'chunk_number': 1, 'content': 'world'},
            {'chunk_number': 0, 'content': 'Hello '}
        ]

        result = self.reassembler.reassemble_message(chunks)
        self.assertEqual(result, 'Hello world')

    def test_send_confirmation(self):
        """Test sending chunk confirmation."""
        mock_interface = Mock()
        mock_interface.sendText.return_value = True

        self.reassembler.send_confirmation('msg-123', 0, 'recipient1', mock_interface)

        mock_interface.sendText.assert_called_once()
        call_args = mock_interface.sendText.call_args[0][0]
        confirmation = json.loads(call_args)
        self.assertEqual(confirmation['type'], 'chunk_confirmation')
        self.assertEqual(confirmation['message_id'], 'msg-123')
        self.assertEqual(confirmation['chunk_number'], 0)

    def test_process_confirmation(self):
        """Test processing chunk confirmation."""
        confirmation_data = {
            'type': 'chunk_confirmation',
            'message_id': 'msg-123',
            'chunk_number': 1
        }

        with patch('backend.database.get_message_chunks') as mock_get:
            with patch('backend.database.mark_chunk_delivered') as mock_mark:
                mock_get.return_value = [
                    {'id': 1, 'chunk_number': 0},
                    {'id': 2, 'chunk_number': 1}
                ]

                self.reassembler.process_confirmation(confirmation_data, 'sender1')

        mock_mark.assert_called_once_with(2)

    def test_confirmations_disabled(self):
        """Test behavior when confirmations are disabled."""
        self.reassembler.enable_confirmations = False
        mock_interface = Mock()

        # Test via process_chunk which checks enable_confirmations
        chunk_data = {
            'message_id': str(uuid.uuid4()),
            'chunk_number': 0,
            'total_chunks': 1,
            'content': 'test'
        }

        with patch('backend.database.insert_message_chunk') as mock_insert:
            with patch('backend.database.get_message_chunks') as mock_get:
                with patch('backend.database.get_delivery_status_for_message') as mock_delivery:
                    with patch('backend.database.complete_message_delivery') as mock_complete:
                        mock_insert.return_value = 1
                        mock_get.return_value = [{
                            'id': 1,
                            'chunk_number': 0,
                            'total_chunks': 1,
                            'content': 'test',
                            'status': 'delivered',
                            'sender_id': 'sender1'
                        }]
                        mock_delivery.return_value = [{'id': 1}]

                        self.reassembler.process_chunk(chunk_data, 'sender1', 'receiver1', mock_interface)

        # Should not send confirmation when disabled
        mock_interface.sendText.assert_not_called()


if __name__ == '__main__':
    unittest.main()