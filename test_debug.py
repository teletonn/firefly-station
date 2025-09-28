import time

def send_message_debug(to_id, full_message, interface=None):
    print("Отправить: " + str(full_message).strip())

    # Safely get our_id with error handling (mocked)
    our_id = 'self'
    receiver_id = 'all' if to_id == 'all' else to_id

    # Chunk the message if it exceeds 200 characters
    # Encode the message to bytes
    message_bytes = full_message.encode('utf-8')
    print(f"Original message: {full_message}")
    print(f"Encoded bytes length: {len(message_bytes)}")
    print(f"Encoded bytes: {message_bytes}")

    chunk_size = 180  # bytes
    byte_chunks = [message_bytes[i:i + chunk_size] for i in range(0, len(message_bytes), chunk_size)]
    print(f"Number of byte chunks: {len(byte_chunks)}")
    for i, chunk in enumerate(byte_chunks):
        print(f"Chunk {i+1} bytes: {chunk} (length: {len(chunk)})")

    # Decode each chunk back to a string
    chunks = [chunk.decode('utf-8', errors='ignore') for chunk in byte_chunks]
    print(f"Decoded chunks: {chunks}")

    reassembled = ''.join(chunks)
    print(f"Reassembled message: {reassembled}")
    print(f"Original == Reassembled: {full_message == reassembled}")

    for i, chunk in enumerate(chunks):
        print("------")
        print(f"Sending chunk {i+1}/{len(chunks)}: {chunk}")
        # Mock send
        if interface:
            if to_id == 'all':
                interface.sendText(chunk, wantAck=True)
            else:
                interface.sendText(chunk, destinationId=to_id, wantAck=True)

        if len(chunks) > 1 and i < len(chunks) - 1:
            time.sleep(0.1)  # Short sleep for debug

# Test cases
test_cases = [
    "привет",  # Short Cyrillic
    "привет мир",  # Medium
    "привет мир, как дела? Это тест сообщения с кириллицей и длинным текстом, который должен быть разбит на несколько чанков для проверки проблем с кодировкой.",  # Long, should span chunks
    "Hello world",  # ASCII for comparison
    "привет мир! 🌍",  # With emoji (4 bytes)
]

# Special test case to simulate mid-character split
special_message = ("привет" * 15).encode('utf-8') + b'\xd0'  # 180 bytes + 1 byte (first byte of 'п')
special_original = ("привет" * 15) + "п"  # For comparison

for i, msg in enumerate(test_cases):
    print(f"\n=== Test Case {i+1}: {msg} ===")
    send_message_debug('all', msg)

# Special test case
print(f"\n=== Special Test Case: Simulated mid-character split ===")
print(f"Original intended: {special_original}")
print(f"Simulated bytes length: {len(special_message)}")
print(f"Simulated bytes: {special_message}")

chunk_size = 180
byte_chunks = [special_message[i:i + chunk_size] for i in range(0, len(special_message), chunk_size)]
print(f"Number of byte chunks: {len(byte_chunks)}")
for i, chunk in enumerate(byte_chunks):
    print(f"Chunk {i+1} bytes: {chunk} (length: {len(chunk)})")

chunks = [chunk.decode('utf-8', errors='ignore') for chunk in byte_chunks]
print(f"Decoded chunks: {chunks}")

reassembled = ''.join(chunks)
print(f"Reassembled message: {reassembled}")
print(f"Original intended == Reassembled: {special_original == reassembled}")
print(f"Data loss: {len(special_original) - len(reassembled)} characters")