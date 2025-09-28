from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import asyncio
from typing import List, Dict, Any
from backend import database, auth
from backend.geolocation import geolocation_service

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_subscriptions: Dict[str, List[WebSocket]] = {}  # Track subscriptions by user/zone

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)

        # Store client info for targeted updates
        if client_id:
            websocket.client_id = client_id
            if client_id not in self.user_subscriptions:
                self.user_subscriptions[client_id] = []
            self.user_subscriptions[client_id].append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from subscriptions
        for client_list in self.user_subscriptions.values():
            if websocket in client_list:
                client_list.remove(websocket)

    async def broadcast(self, message: str):
        """Broadcast to all connected clients."""
        for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

    async def broadcast_to_user(self, user_id: str, message: str):
        """Broadcast to specific user."""
        if user_id in self.user_subscriptions:
            for websocket in self.user_subscriptions[user_id][:]:
                try:
                    await websocket.send_text(message)
                except:
                    self.user_subscriptions[user_id].remove(websocket)

    async def broadcast_to_zone(self, zone_id: str, message: str):
        """Broadcast to all users in a specific zone."""
        # Get users in zone
        users_in_zone = database.get_users_by_zone(int(zone_id))
        for user in users_in_zone:
            await self.broadcast_to_user(user['id'], message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for real-time updates."""
    # For demo purposes, we'll skip authentication for WebSocket
    # In production, you'd implement token-based auth for WebSocket

    await manager.connect(websocket, client_id)
    try:
        # Send initial data
        await send_initial_data(websocket)

        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()

            try:
                client_message = json.loads(data)
                await handle_client_message(websocket, client_message)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def send_initial_data(websocket: WebSocket):
    """Send initial data to newly connected client."""
    try:
        # Send bot statistics
        stats = database.get_bot_stats()
        await websocket.send_text(json.dumps({
            "type": "stats",
            "data": stats
        }))

        # Send recent messages
        messages = database.get_all_messages(limit=10, offset=0)
        await websocket.send_text(json.dumps({
            "type": "messages",
            "data": messages
        }))

        # Send zones data
        zones = database.get_all_zones(limit=100)
        await websocket.send_text(json.dumps({
            "type": "zones",
            "data": zones
        }))

        # Send active users
        users = database.get_all_users(limit=100)
        await websocket.send_text(json.dumps({
            "type": "users",
            "data": users
        }))

        # Send recent alerts
        alerts = database.get_all_alerts(limit=50, include_acknowledged=False)
        await websocket.send_text(json.dumps({
            "type": "alerts",
            "data": alerts
        }))

    except Exception as e:
        print(f"Error sending initial data: {e}")

async def handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle messages from WebSocket clients."""
    message_type = message.get('type')
    data = message.get('data', {})

    if message_type == 'subscribe_user':
        user_id = data.get('user_id')
        if user_id:
            websocket.client_id = user_id
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed",
                "data": {"user_id": user_id}
            }))

    elif message_type == 'subscribe_zone':
        zone_id = data.get('zone_id')
        if zone_id:
            await websocket.send_text(json.dumps({
                "type": "zone_subscription_confirmed",
                "data": {"zone_id": zone_id}
            }))

    elif message_type == 'location_update':
        # Handle location update from client
        user_id = data.get('user_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        altitude = data.get('altitude')
        accuracy = data.get('accuracy')

        if user_id and latitude and longitude:
            # Process location update through geolocation service
            result = geolocation_service.process_location_update(
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                accuracy=accuracy
            )

            # Broadcast location update to relevant clients
            location_update_data = {
                "user_id": user_id,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "timestamp": result.get('update_data', {}).get('location_updated')
            }

            await manager.broadcast(json.dumps({
                "type": "location_update",
                "data": location_update_data
            }))

            # Broadcast zone changes if any
            if result.get('zone_changes', {}).get('zone_changed'):
                zone_change_data = result['zone_changes']
                await manager.broadcast(json.dumps({
                    "type": "zone_change",
                    "data": {
                        "user_id": user_id,
                        "zone_change": zone_change_data
                    }
                }))

            # Broadcast new alerts
            if result.get('alerts'):
                for alert in result['alerts']:
                    await manager.broadcast(json.dumps({
                        "type": "new_alert",
                        "data": alert
                    }))

# Function to broadcast updates (can be called from other parts of the app)
async def broadcast_update(update_type: str, data: dict):
    """Broadcast an update to all connected WebSocket clients."""
    message = json.dumps({
        "type": update_type,
        "data": data,
        "timestamp": asyncio.get_event_loop().time()
    })
    await manager.broadcast(message)

# Real-time location and zone update functions
async def broadcast_location_update(user_id: str, location_data: dict):
    """Broadcast location update for a specific user."""
    update_data = {
        "user_id": user_id,
        "location": location_data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await broadcast_update("location_update", update_data)

async def broadcast_zone_change(user_id: str, zone_change_data: dict):
    """Broadcast zone change for a user."""
    update_data = {
        "user_id": user_id,
        "zone_change": zone_change_data,
        "timestamp": asyncio.get_event_loop().time()
    }
    await broadcast_update("zone_change", update_data)

async def broadcast_new_alert(alert_data: dict):
    """Broadcast new alert to all connected clients."""
    await broadcast_update("new_alert", alert_data)

async def broadcast_zone_update(zone_data: dict):
    """Broadcast zone update (create, update, delete)."""
    await broadcast_update("zone_update", zone_data)

async def broadcast_user_update(user_data: dict):
    """Broadcast user update."""
    await broadcast_update("user_update", user_data)

async def broadcast_statistics_update():
    """Broadcast updated statistics."""
    stats = {
        "bot_stats": database.get_bot_stats(),
        "zone_stats": await get_zone_statistics(),
        "alert_stats": await get_alert_statistics()
    }
    await broadcast_update("statistics_update", stats)

async def get_zone_statistics():
    """Get current zone statistics."""
    try:
        zones = database.get_all_zones(limit=100)
        total_zones = len(zones)
        active_zones = len([z for z in zones if z.get('is_active', True)])

        return {
            "total_zones": total_zones,
            "active_zones": active_zones,
            "zones_by_type": {}
        }
    except Exception as e:
        print(f"Error getting zone statistics: {e}")
        return {}

async def get_alert_statistics():
    """Get current alert statistics."""
    try:
        alerts = database.get_all_alerts(limit=1000, include_acknowledged=False)
        total_alerts = len(alerts)

        severity_counts = {}
        type_counts = {}

        for alert in alerts:
            severity = alert.get('severity', 'medium')
            alert_type = alert.get('alert_type', 'unknown')

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1

        return {
            "total_alerts": total_alerts,
            "by_severity": severity_counts,
            "by_type": type_counts
        }
    except Exception as e:
        print(f"Error getting alert statistics: {e}")
        return {}

# Legacy functions for backward compatibility
async def broadcast_new_message(message_data: dict):
    """Broadcast a new message to all connected clients."""
    await broadcast_update("new_message", message_data)

async def broadcast_stats_update():
    """Broadcast updated statistics to all connected clients."""
    await broadcast_statistics_update()