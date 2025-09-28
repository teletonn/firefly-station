import yaml
import asyncio
import threading
import signal
import time
import platform
import sys
import uuid
import json

# Fix for NotImplementedError on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("Event loop policy set for Windows")
from backend.main import app
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import meshtastic
import meshtastic.ble_interface
import meshtastic.tcp_interface
import meshtastic.serial_interface
from pubsub import pub
from session import UserSession
from session.user_state import UserState
from model import LLMSession
from backend import database
import re

user_sessions: dict[str, UserSession] = {}

config = None

# Global variable to store the asyncio loop for thread-safe operations
main_loop = None

class ChunkDeliveryManager:
    """Manages sequential delivery of message chunks with confirmations, timeouts, and retries."""

    def __init__(self, config):
        self.config = config.get('message_delivery', {})
        self.max_chunks = self.config.get('max_chunks', 16)
        self.chunk_timeout = self.config.get('chunk_timeout_seconds', 60)
        self.max_retries = self.config.get('max_chunk_retries', 3)
        self.inter_chunk_delay = self.config.get('inter_chunk_delay_seconds', 2)
        self.retry_delay = self.config.get('retry_delay_seconds', 15)
        self.max_message_length = self.config.get('max_message_length_bytes', 3200)
        self.metadata_overhead = self.config.get('metadata_overhead_bytes', 50)
        self.enable_chunking = self.config.get('enable_chunking', True)
        self.enable_confirmations = self.config.get('enable_confirmations', True)

    def should_chunk_message(self, message):
        """Determine if a message should be chunked based on size."""
        if not self.enable_chunking:
            return False
        message_bytes = len(message.encode('utf-8'))
        return message_bytes > 200  # Chunk only if message exceeds 200 bytes

    def split_message_into_chunks(self, message, message_id):
        """Split message into chunks with metadata, respecting byte limits."""
        message_bytes = len(message.encode('utf-8'))
        max_payload_bytes = 200  # Meshtastic LoRa payload limit

        if message_bytes <= max_payload_bytes:
            # Return single chunk without metadata
            return [{'content': message}]

        # Calculate max content size for chunked messages (accounting for JSON overhead)
        # Reserve space for metadata: {"message_id":"","chunk_number":0,"total_chunks":0,"content":""}
        # This is approximately 60-80 bytes, so use 120 bytes for content to be safe
        max_content_size = 120

        # Split message into chunks, respecting UTF-8 byte boundaries
        chunks = []
        remaining = message
        chunk_number = 0

        while remaining and chunk_number < self.max_chunks:
            # Find the maximum substring that fits within byte limit
            chunk_content = self._get_chunk_content(remaining, max_content_size)
            if not chunk_content:
                break

            remaining = remaining[len(chunk_content):]

            # Create chunk metadata
            metadata = {
                'message_id': message_id,
                'chunk_number': chunk_number,
                'total_chunks': None,  # Will be set after all chunks are created
                'content': chunk_content
            }

            chunks.append(metadata)
            chunk_number += 1

        # Set total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk['total_chunks'] = total_chunks

        return chunks

    def _get_chunk_content(self, text, max_bytes):
        """Get the largest substring that fits within max_bytes, respecting word boundaries."""
        if len(text.encode('utf-8')) <= max_bytes:
            return text

        # Start with the byte-limited substring
        encoded = text.encode('utf-8')
        truncated = encoded[:max_bytes]

        # Decode back to string, handling potential multi-byte character issues
        try:
            result = truncated.decode('utf-8')
        except UnicodeDecodeError:
            # If decoding fails, try with fewer bytes
            for i in range(1, 4):  # Try removing 1-3 bytes
                try:
                    result = encoded[:max_bytes - i].decode('utf-8')
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Fallback: use a safe substring
                result = text[:max_bytes // 2]  # Very conservative

        # Try to break at word boundary if possible
        if len(result) < len(text):
            last_space = result.rfind(' ')
            if last_space > len(result) * 0.7:  # Don't break too early
                result = result[:last_space]

        return result

    def send_chunk(self, chunk_data, chunk_id, to_id, interface, sender_id):
        """Send a single chunk with retry logic."""
        chunk_json = json.dumps(chunk_data, ensure_ascii=False)
        chunk_bytes = chunk_json.encode('utf-8')

        # Check if chunk fits within Meshtastic payload limit
        max_payload_bytes = 200
        if len(chunk_bytes) > max_payload_bytes:
            print(f"Error: Chunk too large ({len(chunk_bytes)} bytes), exceeds Meshtastic limit of {max_payload_bytes}")
            database.mark_chunk_failed(chunk_id)
            return False

        success = False
        for attempt in range(self.max_retries):
            try:
                if to_id == 'all':
                    interface.sendText(chunk_json, wantAck=True)
                else:
                    interface.sendText(chunk_json, destinationId=to_id, wantAck=True)
                success = True

                # Mark chunk as sent in database
                database.mark_chunk_sent(chunk_id)

                break
            except Exception as e:
                print(f"Failed to send chunk {chunk_data.get('chunk_number', 'unknown')}, attempt {attempt+1}/{self.max_retries}: {e}")
                database.increment_chunk_retry_count(chunk_id)
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

        if not success:
            print(f"All {self.max_retries} retries failed for chunk {chunk_data.get('chunk_number', 'unknown')}")
            database.mark_chunk_failed(chunk_id)

        return success

    def send_message_chunks(self, message, to_id, interface, sender_id, receiver_id):
        """Send a message using chunked delivery."""
        message_id = str(uuid.uuid4())

        chunks = self.split_message_into_chunks(message, message_id)

        if len(chunks) == 1 and 'message_id' not in chunks[0]:
            # Send as single message
            return self.send_single_message(message, to_id, interface, sender_id, receiver_id)

        # Chunked message
        total_chunks = len(chunks)
        delivery_id = database.insert_delivery_status(message_id, sender_id, receiver_id, total_chunks)

        # Insert all chunks into database
        for i, chunk in enumerate(chunks):
            chunk_id = database.insert_message_chunk(
                message_id=message_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                chunk_number=i,
                total_chunks=total_chunks,
                content=chunk['content']
            )
            chunk['chunk_id'] = chunk_id

        # Send chunks sequentially
        for i, chunk in enumerate(chunks):
            print(f"Sending chunk {i+1}/{total_chunks} for message {message_id}")
            success = self.send_chunk(chunk, chunk['chunk_id'], to_id, interface, sender_id)

            if not success:
                print(f"Failed to send chunk {i+1}, aborting message delivery")
                break

            # Wait between chunks
            if i < total_chunks - 1:
                time.sleep(self.inter_chunk_delay)

        return message_id

    def send_single_message(self, message, to_id, interface, sender_id, receiver_id):
        """Send a message as a single chunk (for small messages)."""
        message_id = str(uuid.uuid4())

        # Check message size
        message_bytes = len(message.encode('utf-8'))
        if message_bytes > 200:
            print(f"Message too large ({message_bytes} bytes), switching to chunked delivery")
            return self.send_message_chunks(message, to_id, interface, sender_id, receiver_id)

        # Store as single chunk
        chunk_id = database.insert_message_chunk(
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            chunk_number=0,
            total_chunks=1,
            content=message
        )

        # Send directly
        success = False
        for attempt in range(self.max_retries):
            try:
                if to_id == 'all':
                    interface.sendText(message, wantAck=True)
                else:
                    interface.sendText(message, destinationId=to_id, wantAck=True)
                success = True
                database.mark_chunk_sent(chunk_id)
                break
            except Exception as e:
                print(f"Failed to send message, attempt {attempt+1}/{self.max_retries}: {e}")
                database.increment_chunk_retry_count(chunk_id)
                if attempt < self.max_retries - 1:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

        if not success:
            print(f"All {self.max_retries} retries failed for message")
            database.mark_chunk_failed(chunk_id)

        return message_id


class MessageReassembler:
    """Reassembles chunked messages and manages confirmations."""

    def __init__(self, config):
        self.config = config.get('message_delivery', {})
        self.enable_confirmations = self.config.get('enable_confirmations', True)

    def process_chunk(self, chunk_data, sender_id, receiver_id, interface):
        """Process a received chunk and send confirmation if enabled."""
        try:
            # Parse chunk data
            if isinstance(chunk_data, str):
                chunk = json.loads(chunk_data)
            elif isinstance(chunk_data, dict):
                chunk = chunk_data
            else:
                print(f"Invalid chunk data type: {type(chunk_data)}, expected str or dict")
                return None

            # Ensure chunk is a dictionary
            if not isinstance(chunk, dict):
                print(f"Chunk data is not a dictionary: {type(chunk)}")
                return None

            message_id = chunk.get('message_id')
            chunk_number = chunk.get('chunk_number')
            total_chunks = chunk.get('total_chunks')
            content = chunk.get('content')

            if not all([message_id, chunk_number is not None, total_chunks, content]):
                print("Invalid chunk format, ignoring")
                return None

            # Store chunk in database
            chunk_id = database.insert_message_chunk(
                message_id=message_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                chunk_number=chunk_number,
                total_chunks=total_chunks,
                content=content,
                status='delivered'
            )

            # Send confirmation if enabled
            if self.enable_confirmations:
                self.send_confirmation(message_id, chunk_number, sender_id, interface)

            # Check if message is complete
            return self.check_message_complete(message_id, receiver_id)

        except json.JSONDecodeError as e:
            print(f"Failed to parse chunk JSON: {e}, treating as regular message")
            return None
        except Exception as e:
            print(f"Error processing chunk: {type(e).__name__}: {e}")
            return None

    def send_confirmation(self, message_id, chunk_number, recipient_id, interface):
        """Send confirmation for received chunk."""
        try:
            confirmation = {
                'type': 'chunk_confirmation',
                'message_id': message_id,
                'chunk_number': chunk_number,
                'timestamp': time.time()
            }
            confirmation_json = json.dumps(confirmation)

            interface.sendText(confirmation_json, destinationId=recipient_id, wantAck=False)
            print(f"Sent confirmation for chunk {chunk_number} of message {message_id}")
        except Exception as e:
            print(f"Failed to send confirmation: {e}")

    def check_message_complete(self, message_id, receiver_id):
        """Check if all chunks for a message have been received."""
        chunks = database.get_message_chunks(message_id)
        if not chunks:
            return None

        total_chunks = chunks[0]['total_chunks']
        delivered_chunks = sum(1 for chunk in chunks if chunk['status'] == 'delivered')

        if delivered_chunks == total_chunks:
            # Message is complete, reassemble it
            reassembled_message = self.reassemble_message(chunks)

            # Mark delivery as complete
            delivery_status = database.get_delivery_status_for_message(message_id)
            if delivery_status:
                database.complete_message_delivery(delivery_status[0]['id'])

            return {
                'message_id': message_id,
                'sender_id': chunks[0]['sender_id'],
                'receiver_id': receiver_id,
                'full_message': reassembled_message
            }

        return None

    def reassemble_message(self, chunks):
        """Reassemble message from chunks."""
        # Sort chunks by chunk_number
        sorted_chunks = sorted(chunks, key=lambda x: x['chunk_number'])

        # Concatenate content
        full_message = ''.join(chunk['content'] for chunk in sorted_chunks)
        return full_message

    def process_confirmation(self, confirmation_data, sender_id):
        """Process a chunk confirmation."""
        try:
            if isinstance(confirmation_data, str):
                conf = json.loads(confirmation_data)
            else:
                conf = confirmation_data

            if conf.get('type') != 'chunk_confirmation':
                return

            message_id = conf.get('message_id')
            chunk_number = conf.get('chunk_number')

            if message_id and chunk_number is not None:
                # Find and mark chunk as confirmed
                chunks = database.get_message_chunks(message_id)
                for chunk in chunks:
                    if chunk['chunk_number'] == chunk_number:
                        database.mark_chunk_delivered(chunk['id'])
                        print(f"Chunk {chunk_number} of message {message_id} confirmed")
                        break

        except Exception as e:
            print(f"Error processing confirmation: {e}")


# Global instances
chunk_delivery_manager = None
message_reassembler = None

def get_node_summary(node_data):
    user_info = node_data.get("user", {})
    position = node_data.get("position", {})
    metrics = node_data.get("deviceMetrics", {})

    summary = (
        f"ID ноды: {user_info.get('id', 'Unknown')}\n"
        f"Имя: {user_info.get('longName', 'Unknown')}\n"
        f"Короткое имя: {user_info.get('shortName', 'Unknown')}\n"
        f"Батарея: {metrics.get('batteryLevel', 'Unknown')}%\n"
        f"Позиция: "
        f"Ш: {position.get('latitude', 'N/A')}, "
        f"Д: {position.get('longitude', 'N/A')}, "
        f"В: {position.get('altitude', 'N/A')}m\n"
    )

    return summary

def split_message(message, max_bytes=200):
    """
    Split message into chunks respecting UTF-8 byte limit and word boundaries.
    If a word doesn't fit in the current chunk, move it entirely to the next chunk.
    Each chunk is a separate message.
    """
    if not message:
        return ['']
    words = re.findall(r'\S+|\n', message)
    if not words:
        return ['']
    chunks = []
    current_chunk = ""
    for word in words:
        if current_chunk:
            if word == '\n':
                test_chunk = current_chunk + word
            else:
                test_chunk = current_chunk + ' ' + word
        else:
            test_chunk = word
        if len(test_chunk.encode('utf-8')) > max_bytes:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = word
            else:
                # If word exceeds limit, add it anyway (assuming words are not too long)
                chunks.append(word)
                current_chunk = ""
        else:
            current_chunk = test_chunk
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def send_message(to_id, full_message, interface):
    """
    Send a message via the Firefly interface using chunked delivery.
    """
    print("Sending: " + str(full_message).strip())

    # Safely get our_id with error handling
    try:
        if interface.myInfo and hasattr(interface.myInfo, 'get'):
            our_id = interface.myInfo.get('user', {}).get('id', str(interface.myInfo.get('myNodeNum', 'self')))
        else:
            our_id = 'self'
    except AttributeError:
        our_id = 'self'

    receiver_id = 'all' if to_id == 'all' else to_id

    # Store outgoing message in history
    database.insert_message(our_id, receiver_id, full_message, "outgoing")

    # Use chunk delivery manager to send the message
    if chunk_delivery_manager:
        message_id = chunk_delivery_manager.send_message_chunks(full_message, to_id, interface, our_id, receiver_id)
        print(f"Message sent with ID: {message_id}")
    else:
        # Fallback to old method if manager not initialized
        print("Warning: ChunkDeliveryManager not initialized, using fallback")
        message_chunks = split_message(full_message, 200)

        for i, chunk in enumerate(message_chunks):
            print(f"Sending chunk {i+1}/{len(message_chunks)}: {chunk}")
            success = False
            max_retries = 3
            retry_delay = 15

            for attempt in range(max_retries):
                try:
                    if to_id == 'all':
                        interface.sendText(chunk, wantAck=True)
                    else:
                        interface.sendText(chunk, destinationId=to_id, wantAck=True)
                    success = True
                    break
                except Exception as e:
                    print(f"Failed to send chunk {i+1}, attempt {attempt+1}/{max_retries}: {e}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)

            if not success:
                print(f"All {max_retries} retries failed for chunk {i+1}, skipping to next.")
                continue

            # Pause between chunks if there are more
            if len(message_chunks) > 1 and i < len(message_chunks) - 1:
                time.sleep(2)  # Use shorter delay like the manager

def onReceive(packet, interface):  # called when a packet arrives
    try:
        sender = "all" if packet.get('toId') == '^all' else str(packet.get("fromId", "unknown"))

        # Safely get node_data with error handling
        try:
            if interface.nodes and hasattr(interface.nodes, 'get'):
                node_info = interface.nodes.get(str(packet.get("fromId", "unknown")), {})
            else:
                node_info = {}
        except AttributeError:
            node_info = {}

        node_data = get_node_summary(node_info)

        # Safely get our_id with error handling
        try:
            if interface.myInfo and hasattr(interface.myInfo, 'get'):
                our_id = interface.myInfo.get('user', {}).get('id', str(interface.myInfo.get('myNodeNum', 'self')))
            else:
                our_id = 'self'
        except AttributeError:
            our_id = 'self'

        # Store user data
        print(f"Storing user data for {packet.get('fromId', 'unknown')}")
        database.insert_or_update_user(str(packet.get("fromId", "unknown")), node_info)

        # Process location data through geolocation service
        user_id = str(packet.get("fromId", "unknown"))
        position = node_info.get("position", {})

        if position.get('latitude') is not None and position.get('longitude') is not None:
            try:
                from backend.geolocation import geolocation_service
                from backend.routers.geolocation import broadcast_location_update, broadcast_zone_change, broadcast_new_alert

                # Process location update
                result = geolocation_service.process_location_update(
                    user_id=user_id,
                    latitude=position.get('latitude'),
                    longitude=position.get('longitude'),
                    altitude=position.get('altitude'),
                    battery_level=node_info.get('deviceMetrics', {}).get('batteryLevel')
                )

                if result['success']:
                    print(f"Processed location update for {user_id}: moving={result['is_moving']}, speed={result['speed_mps']:.2f}m/s")

                    # Broadcast real-time updates
                    asyncio.run_coroutine_threadsafe(broadcast_location_update(user_id, {
                        'latitude': position.get('latitude'),
                        'longitude': position.get('longitude'),
                        'altitude': position.get('altitude'),
                        'is_moving': result['is_moving'],
                        'speed_mps': result['speed_mps']
                    }), main_loop)

                    # Broadcast zone changes
                    if result['zone_changes'].get('zone_changed'):
                        asyncio.run_coroutine_threadsafe(broadcast_zone_change(user_id, result['zone_changes']), main_loop)

                    # Broadcast new alerts
                    for alert in result['alerts']:
                        asyncio.run_coroutine_threadsafe(broadcast_new_alert(alert), main_loop)

                else:
                    print(f"Failed to process location update for {user_id}")

            except Exception as e:
                print(f"Error processing geolocation data for {user_id}: {e}")

        text_message_present =  "decoded" in packet and "text" in packet.get("decoded", {})

        if text_message_present:
            received_text = packet.get("decoded", {}).get("text", "")

            print(f"Сообщение от {sender}: {received_text}")

            # Check if this is a chunked message or confirmation
            if message_reassembler:
                # Try to process as chunk
                complete_message = message_reassembler.process_chunk(received_text, sender, our_id, interface)

                # Try to process as confirmation
                message_reassembler.process_confirmation(received_text, sender)

                if complete_message:
                    # Message is complete, use the reassembled message
                    full_message = complete_message['full_message']
                    print(f"Reassembled message from {sender}: {full_message}")

                    # Store the complete incoming message in history
                    receiver_id = 'all' if packet.get('toId') == '^all' else our_id
                    database.insert_message(sender, receiver_id, full_message, "incoming")

                    # Handle !help command on channel 0
                    if packet.get('toId') == '^all':
                        if full_message.strip() == '!help':
                            help_msg = config.get('help_message', 'Help message not configured.')
                            target = str(packet.get("fromId", "unknown"))
                            send_message(target, help_msg, interface)
                        # For any other message on channel 0, do nothing.
                        return

                    if sender not in user_sessions:
                        user_sessions[sender] = UserSession(sender, node_data)

                    response = user_sessions[sender].chat(full_message)

                    if response != "":
                        # Always respond as DM to the sender for non-channel-0 messages
                        target = str(packet.get("fromId", "unknown"))
                        send_message(target, response, interface)
                else:
                    # Not a complete chunked message, treat as regular message
                    # Store incoming message
                    receiver_id = 'all' if packet.get('toId') == '^all' else our_id
                    database.insert_message(str(packet.get("fromId", "unknown")), receiver_id, received_text, "incoming")

                    # Handle !help command on channel 0
                    if packet.get('toId') == '^all':
                        if received_text.strip() == '!help':
                            help_msg = config.get('help_message', 'Help message not configured.')
                            target = str(packet.get("fromId", "unknown"))
                            send_message(target, help_msg, interface)
                        # For any other message on channel 0, do nothing.
                        return

                    if sender not in user_sessions:
                        user_sessions[sender] = UserSession(sender, node_data)

                    response = user_sessions[sender].chat(received_text)

                    if response != "":
                        # Always respond as DM to the sender for non-channel-0 messages
                        target = str(packet.get("fromId", "unknown"))
                        send_message(target, response, interface)
            else:
                # Fallback to old behavior if reassembler not initialized
                # Store incoming message
                receiver_id = 'all' if packet.get('toId') == '^all' else our_id
                database.insert_message(str(packet.get("fromId", "unknown")), receiver_id, received_text, "incoming")

                # Handle !help command on channel 0
                if packet.get('toId') == '^all':
                    if received_text.strip() == '!help':
                        help_msg = config.get('help_message', 'Help message not configured.')
                        target = str(packet.get("fromId", "unknown"))
                        send_message(target, help_msg, interface)
                    # For any other message on channel 0, do nothing.
                    return

                if sender not in user_sessions:
                    user_sessions[sender] = UserSession(sender, node_data)

                response = user_sessions[sender].chat(received_text)

                if response != "":
                    # Always respond as DM to the sender for non-channel-0 messages
                    target = str(packet.get("fromId", "unknown"))
                    send_message(target, response, interface)

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}") # Prints error type and message

def onConnection(interface, topic=pub.AUTO_TOPIC): # called when we (re)connect to the radio
    print("Успешно подключен к устройству!")

def run_bot(shutdown_event):
    pub.subscribe(onReceive, "meshtastic.receive")
    pub.subscribe(onConnection, "meshtastic.connection.established")

    interface = meshtastic.tcp_interface.TCPInterface(hostname="192.168.1.245")

    try:
        while not shutdown_event.is_set():
            time.sleep(1)
    finally:
        interface.close()

async def main():
    global config, chunk_delivery_manager, message_reassembler
    with open('config.yaml', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Initialize chunk delivery manager and message reassembler
    chunk_delivery_manager = ChunkDeliveryManager(config)
    message_reassembler = MessageReassembler(config)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config['web_server']['cors_origins'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    shutdown_event = threading.Event()

    # Start bot thread
    bot_thread = threading.Thread(target=run_bot, args=(shutdown_event,))
    bot_thread.start()

    # Start web server
    config_uvicorn = uvicorn.Config(app, host=config['web_server']['host'], port=config['web_server']['port'])
    server = uvicorn.Server(config_uvicorn)

    # Handle shutdown
    def signal_handler():
        shutdown_event.set()
        server.should_exit = True

    print("About to get running loop")
    loop = asyncio.get_running_loop()
    global main_loop
    main_loop = loop

    if sys.platform != "win32":
        print("Setting up signal handlers for non-Windows")
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    try:
        await server.serve()
    except KeyboardInterrupt:
        print("KeyboardInterrupt caught, calling signal_handler")
        # On Windows, KeyboardInterrupt is used for shutdown
        signal_handler()
    finally:
        # Wait for bot thread to finish asynchronously
        if bot_thread.is_alive():
            await loop.run_in_executor(None, bot_thread.join)

if __name__ == "__main__":
    print("About to run asyncio.run(main())")
    asyncio.run(main())