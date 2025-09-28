# LLM/Bot Platform with Светлячок

This repository provides a platform for integrating Large Language Models (LLMs) or Old-school Bots with the Светлячок mesh communication network. It allows users on the mesh network to interact with an LLM for concise, automated responses.

Furthermore, this platform also allows users to execute tasks through LLM, such as:

- Calling emergency services
- Sending messages
- Retrieving info from sensors

**Note: Currently the only supported tool is a demo for emergency service. More tools are coming soon. You can add your own tool using the guide below**

## Features

- Bi-directional communication between Светлячок and an LLM.
- Support for general broadcast or targeted responses.
- Automatic message chunking for long responses exceeding 200 characters.
- Maintains message history for context-aware interactions.
- Node-specific information (e.g., battery level, location) can be included in responses.
- Tool Use: Your LLM can execute tasks for you based on your prompt
- Old-school bots features: anything you can imagine with a basic telegram or discord bots.

## Requirements

- Python 3.8+
- Светлячок Python library
- Ollama LLM Python SDK
- PubSub library

## Quick Start

### Option 1: Unified Launcher (Recommended)

1. Connect your Светлячок device via USB or configure it for TCP access.
2. Clone this repository:
   ```bash
   git clone <repo_url>
   cd <repo_name>
   ```
3. Run the unified launcher:
   ```bash
   # On Windows
   launch.bat

   # On Linux/Mac
   python launch.py
   ```

The launcher will:
- ✅ Check system requirements
- 📦 Install Python dependencies
- 🔨 Build the React frontend
- 🚀 Start both bot and web server

### Option 2: Manual Setup

1. Connect your Светлячок device via USB or configure it for TCP access.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Build the frontend (optional, for admin interface):
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
4. Run the system:
   ```bash
   python main.py
   ```

### Web Interface

Once running, access the admin interface at:
- **Admin Panel**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

The admin panel provides:
- 📊 Real-time dashboard with bot statistics
- 👥 User management
- 💬 Message monitoring
- 🤖 Bot controls
- 📋 Audit logs
- 🔐 Authentication system

### Светлячок Interaction

5. To talk with the LLM, send messages via Светлячок:
   - Normal messages for LLM chat
   - `/tool your_message` to activate tool use
   - `/enable_llm` / `/disable_llm` for LLM features
   - `/enable_echo` / `/disable_echo` for testing

**Ollama performace with Tool Use on small model (llama 3.2:3b) is not exactly correct. Please test your model extensively before putting it into real use.**

## How to use

Radio LLM works like a discord chat bot. You can send commands into the channel to configure chat or run commands.

```
For LLM chat features
/enable_llm
/disable_llm
For echo features to test meshtastic
/enable_echo
/disable_echo
```

## Configuration

- Modify the LLM model by updating the `chat` function in `chat_with_llm`.
- Adjust chunk size or message length limits as needed.

### Custom Tools

To add your own tool:

1. Define your tool in **model/tool_handler.py**
2. Register your tool in **model/tool_registry.py**
3. Describe your tool in **config.yaml**

Please use the same name for your tool across all steps. In the future, this process will be streamlined.

### Different Interface

If you use BLE on your computer, please check Светлячок documentation [here](https://meshtastic.org/docs/software/python/cli/usage/#utilizing-ble-via-the-python-cli) first. It will help you navigate the meshtastic cli to search for devices and how to authenticate the connection.

```python
# Use this if your node is connected to your local network
interface = meshtastic.tcp_interface.TCPInterface(hostname="meshtastic.local")

# Use this if your node is on BLE
# Before using BLE client, you should connect to your device using your system bluetooth settings.
# Read more on https://meshtastic.org/docs/software/python/cli/usage/#utilizing-ble-via-the-python-cli
interface = meshtastic.ble_interface.BLEClient(address="Your Node BLE Identifier")

# Use this if your node is connected to your computer
interface = meshtastic.serial_interface.SerialInterface() # add param devPath if you have multiple devices connected
```

### Ollama Model

If you use Ollama, please change the model name in model/config.yaml to your installed model.

## How It Works

1. **Receiving Messages**:

   - The script listens for incoming messages on the Светлячок network.
   - Received messages trigger the LLM to generate a response.

2. **Generating Responses**:

   - The `chat_with_llm` function interacts with the LLM using the `ollama` library.
   - Responses are concise and limited to 200 characters.

3. **Sending Responses**:

   - Responses are sent back to the sender or broadcasted to the network.
   - Messages exceeding 200 characters are sent in chunks.

4. **Node-Specific Information**:

- The script can retrieve and include specific details about the sending node, such as:
  - Node ID
  - Battery level
  - Location (latitude, longitude, altitude)
  - Last heard time
- This information can be appended to responses for context-aware conversations.

## Key Components

- `onReceive(packet, interface)`: Handles incoming messages.
- `chat_with_llm(user_id, message)`: Queries the LLM and returns a response.
- `onConnection(interface)`: Manages connection to the Светлячок device.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributions

Feel free to submit issues or pull requests for improvements or bug fixes.

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError for backend**
   - Solution: Ensure you're running from the project root directory
   - The `__init__.py` file in the root should resolve import issues

2. **Frontend not loading**
   - Solution: Build the React frontend manually:
     ```bash
     cd frontend
     npm install
     npm run build
     cd ..
     ```

3. **Светлячок connection failed**
   - Check your device IP address in `main.py` (currently set to `192.168.1.135`)
   - Ensure your Светлячок device is connected to the network
   - Try different connection methods (TCP, BLE, Serial)

4. **Port 8000 already in use**
   - Change the port in `config.yaml` under `web_server.port`
   - Or stop other services using port 8000

5. **Database errors**
   - Delete `meshtastic_llm.db` and restart (will recreate tables)
   - Check file permissions for database file

### System Requirements

- Python 3.8+
- Node.js 16+ (for frontend building)
- Светлячок device connected to network
- Internet connection for LLM services

## Disclaimer

Ensure compliance with local laws and regulations when using Светлячок devices and LLMs.
