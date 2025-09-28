import sqlite3
import datetime
import os
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'meshtastic_llm.db'

def get_connection():
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database and create tables if they don't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                long_name TEXT,
                short_name TEXT,
                battery_level INTEGER,
                latitude REAL,
                longitude REAL,
                altitude REAL,
                last_seen TIMESTAMP,
                nickname TEXT,
                public_key TEXT,
                private_key TEXT,
                registration_status TEXT DEFAULT 'unregistered'
            )
        ''')

        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                receiver_id TEXT,
                text TEXT,
                timestamp TIMESTAMP,
                direction TEXT
            )
        ''')

        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                state TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create pending_messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_id TEXT,
                sender_id TEXT,
                text TEXT,
                timestamp TIMESTAMP,
                delivered BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (recipient_id) REFERENCES users (id),
                FOREIGN KEY (sender_id) REFERENCES users (id)
            )
        ''')

        # Create admin_users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Create roles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                permissions TEXT NOT NULL  -- JSON string of permissions
            )
        ''')

        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                resource_id TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                FOREIGN KEY (admin_user_id) REFERENCES admin_users (id)
            )
        ''')

        # Insert default roles if not exist
        cursor.execute('''
            INSERT OR IGNORE INTO roles (name, permissions)
            VALUES ('super_admin', '["all"]'), ('admin', '["users", "messages", "audit", "bot_controls", "zones", "alerts", "analytics", "processes"]'), ('viewer', '["users:read", "messages:read", "audit:read"]')
        ''')

        # Update admin role permissions if needed
        cursor.execute('''
            UPDATE roles SET permissions = '["users", "messages", "audit", "bot_controls", "zones", "alerts", "analytics", "processes"]' WHERE name = 'admin'
        ''')

        # Create zones table for geofencing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                center_latitude REAL NOT NULL,
                center_longitude REAL NOT NULL,
                radius_meters REAL NOT NULL,
                zone_type TEXT DEFAULT 'circular', -- 'circular', 'polygon'
                coordinates TEXT, -- JSON string for polygon coordinates
                is_active BOOLEAN DEFAULT TRUE,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create user_groups table for user grouping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create user_group_members table for many-to-many relationship
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (group_id) REFERENCES user_groups (id),
                FOREIGN KEY (added_by) REFERENCES admin_users (id),
                UNIQUE(user_id, group_id)
            )
        ''')

        # Create alerts table for alert management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                zone_id INTEGER,
                alert_type TEXT NOT NULL, -- 'zone_entry', 'zone_exit', 'speeding', 'offline', 'battery_low'
                severity TEXT DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                location_latitude REAL,
                location_longitude REAL,
                is_acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_by INTEGER,
                acknowledged_at TIMESTAMP,
                is_resolved BOOLEAN DEFAULT FALSE,
                resolved_by INTEGER,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (zone_id) REFERENCES zones (id),
                FOREIGN KEY (acknowledged_by) REFERENCES admin_users (id),
                FOREIGN KEY (resolved_by) REFERENCES admin_users (id)
            )
        ''')

        # Create alert_rules table for alert configuration rules
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                alert_type TEXT NOT NULL, -- 'zone_entry', 'zone_exit', 'speeding', 'offline', 'battery_low'
                severity TEXT DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
                zone_id INTEGER, -- NULL for all zones
                conditions TEXT, -- JSON string of conditions
                target_groups TEXT, -- JSON array of group IDs
                escalation_rules TEXT, -- JSON string of escalation rules
                is_active BOOLEAN DEFAULT TRUE,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (zone_id) REFERENCES zones (id),
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create alert_escalation_rules table for alert escalation management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_escalation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                rules TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alert_id) REFERENCES alerts (id),
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create location_history table for tracking data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                altitude REAL,
                accuracy REAL, -- GPS accuracy in meters
                speed REAL, -- Speed in m/s
                heading REAL, -- Direction of movement in degrees
                battery_level INTEGER,
                is_moving BOOLEAN DEFAULT FALSE,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create location_cache table for offline support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                altitude REAL,
                accuracy REAL,
                speed REAL,
                heading REAL,
                battery_level INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced BOOLEAN DEFAULT FALSE,
                synced_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create bot_triggers table for advanced trigger management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT NOT NULL, -- 'keyword', 'emoji', 'location', 'time', 'user_activity'
                trigger_config TEXT NOT NULL, -- JSON configuration for trigger parameters
                conditions TEXT, -- JSON array of conditions (AND/OR logic)
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                cooldown_seconds INTEGER DEFAULT 0,
                last_triggered TIMESTAMP,
                trigger_count INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create bot_responses table for response templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                response_type TEXT NOT NULL, -- 'text', 'template', 'dynamic'
                content TEXT NOT NULL, -- Template content or static response
                variables TEXT, -- JSON array of available variables
                language TEXT DEFAULT 'en', -- 'en', 'ru', etc.
                target_type TEXT DEFAULT 'all', -- 'all', 'user', 'group', 'zone'
                target_ids TEXT, -- JSON array of target IDs
                channels TEXT, -- JSON array of channels to send to
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                usage_count INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create bot_trigger_logs table for trigger execution tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_trigger_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER NOT NULL,
                user_id TEXT,
                message_text TEXT,
                trigger_data TEXT, -- JSON data about what triggered it
                matched_conditions TEXT, -- JSON array of matched conditions
                executed_responses TEXT, -- JSON array of executed response IDs
                execution_time_ms INTEGER,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trigger_id) REFERENCES bot_triggers (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create bot_response_logs table for response delivery tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_response_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER NOT NULL,
                trigger_log_id INTEGER,
                user_id TEXT,
                channel TEXT NOT NULL,
                content TEXT NOT NULL,
                delivery_status TEXT DEFAULT 'sent', -- 'sent', 'delivered', 'failed'
                delivery_time_ms INTEGER,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (response_id) REFERENCES bot_responses (id),
                FOREIGN KEY (trigger_log_id) REFERENCES bot_trigger_logs (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create message_chunks table for message chunking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                chunk_number INTEGER NOT NULL,
                total_chunks INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                confirmed_at TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        ''')

        # Create message_delivery_status table for tracking chunk delivery
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_delivery_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                sender_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                total_chunks INTEGER NOT NULL,
                delivered_chunks INTEGER DEFAULT 0,
                status TEXT DEFAULT 'in_progress',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        ''')

        # Create processes table for workflow management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                template_id INTEGER,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                execution_count INTEGER DEFAULT 0,
                last_executed TIMESTAMP,
                success_rate REAL DEFAULT 0.0,
                avg_execution_time REAL,
                FOREIGN KEY (template_id) REFERENCES process_templates (id),
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Create process_triggers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL, -- 'zone_entry', 'zone_exit', 'alert_created', 'message_received', 'time_schedule', 'manual'
                trigger_config TEXT NOT NULL, -- JSON configuration
                conditions TEXT, -- JSON conditions (AND/OR logic)
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (process_id) REFERENCES processes (id)
            )
        ''')

        # Create process_actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                action_type TEXT NOT NULL, -- 'send_message', 'create_alert', 'update_zone', 'trigger_bot', 'update_user_group', 'send_notification'
                action_config TEXT NOT NULL, -- JSON configuration
                conditions TEXT, -- JSON conditions for execution
                action_order INTEGER NOT NULL,
                timeout_seconds INTEGER DEFAULT 30,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (process_id) REFERENCES processes (id)
            )
        ''')

        # Create process_executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                triggered_by TEXT, -- user_id or 'system'
                trigger_event TEXT, -- JSON event data
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running', -- 'running', 'completed', 'failed', 'timeout'
                error_message TEXT,
                execution_time_ms INTEGER,
                steps_completed INTEGER DEFAULT 0,
                total_steps INTEGER,
                FOREIGN KEY (process_id) REFERENCES processes (id)
            )
        ''')

        # Create process_execution_steps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_execution_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER NOT NULL,
                action_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'skipped'
                result TEXT, -- JSON result data
                error_message TEXT,
                execution_time_ms INTEGER,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (execution_id) REFERENCES process_executions (id),
                FOREIGN KEY (action_id) REFERENCES process_actions (id)
            )
        ''')

        # Create process_templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT, -- 'emergency', 'maintenance', 'communication', 'monitoring'
                template_data TEXT NOT NULL, -- JSON template structure
                usage_count INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_public BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (created_by) REFERENCES admin_users (id)
            )
        ''')

        # Add geolocation-specific fields to users table
        try:
            # Check if columns exist before adding them
            cursor.execute("PRAGMA table_info(users)")
            columns = [column['name'] for column in cursor.fetchall()]

            if 'tracking_enabled' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN tracking_enabled BOOLEAN DEFAULT TRUE')
            if 'tracking_interval_active' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN tracking_interval_active INTEGER DEFAULT 600')
            if 'tracking_interval_stationary' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN tracking_interval_stationary INTEGER DEFAULT 14400')
            if 'last_motion_detection' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN last_motion_detection TIMESTAMP')
            if 'current_zone_id' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN current_zone_id INTEGER')
            if 'group_id' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN group_id INTEGER')
            if 'device_status' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN device_status TEXT DEFAULT "online"')
            if 'last_location_update' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN last_location_update TIMESTAMP')
            if 'created_at' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

        except sqlite3.Error as e:
            logger.warning(f"Some user table alterations may have failed (columns might already exist): {e}")

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location_history_user_time ON location_history(user_id, recorded_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location_history_recorded_at ON location_history(recorded_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_user_created ON alerts(user_id, created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_zone_created ON alerts(zone_id, created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(is_acknowledged, created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_zones_active ON zones(is_active, created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_tracking ON users(tracking_enabled, last_location_update)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_zone ON users(current_zone_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location_cache_synced ON location_cache(synced, recorded_at)')

        # Indexes for message chunks and delivery status
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_chunks_message_id ON message_chunks(message_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_chunks_status ON message_chunks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_delivery_status_message_id ON message_delivery_status(message_id)')

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
        raise

def insert_or_update_user(user_id, user_data):
    """Insert or update user data."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        user_info = user_data.get("user", {})
        position = user_data.get("position", {})
        metrics = user_data.get("deviceMetrics", {})

        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        existing = cursor.fetchone()

        if existing:
            # Update existing user, preserve nickname, keys, status
            cursor.execute('''
                UPDATE users SET long_name = ?, short_name = ?, battery_level = ?, latitude = ?, longitude = ?, altitude = ?, last_seen = ?
                WHERE id = ?
            ''', (
                user_info.get('longName'),
                user_info.get('shortName'),
                metrics.get('batteryLevel'),
                position.get('latitude'),
                position.get('longitude'),
                position.get('altitude'),
                datetime.datetime.now(),
                user_id
            ))
            logger.info(f"Updated existing user {user_id}, preserved keys and status")
        else:
            # Insert new user
            cursor.execute('''
                INSERT INTO users (id, long_name, short_name, battery_level, latitude, longitude, altitude, last_seen, created_at, nickname, public_key, private_key, registration_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, 'unregistered')
            ''', (
                user_id,
                user_info.get('longName'),
                user_info.get('shortName'),
                metrics.get('batteryLevel'),
                position.get('latitude'),
                position.get('longitude'),
                position.get('altitude'),
                datetime.datetime.now(),
                datetime.datetime.now()
            ))
            logger.info(f"Inserted new user {user_id}")

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error inserting/updating user {user_id}: {e}")

def insert_message(sender_id, receiver_id, text, direction):
    """Insert a message into the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, text, timestamp, direction)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender_id, receiver_id, text, datetime.datetime.now(), direction))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error inserting message from {sender_id} to {receiver_id}: {e}")

def insert_session(user_id, state):
    """Insert a new session."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO sessions (user_id, start_time, state)
            VALUES (?, ?, ?)
        ''', (user_id, datetime.datetime.now(), state))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id
    except sqlite3.Error as e:
        logger.error(f"Error inserting session for {user_id}: {e}")
        return None

def update_session(session_id, end_time=None, state=None):
    """Update session with end time and/or state."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if end_time and state:
            cursor.execute('''
                UPDATE sessions SET end_time = ?, state = ? WHERE id = ?
            ''', (end_time, state, session_id))
        elif end_time:
            cursor.execute('''
                UPDATE sessions SET end_time = ? WHERE id = ?
            ''', (end_time, session_id))
        elif state:
            cursor.execute('''
                UPDATE sessions SET state = ? WHERE id = ?
            ''', (state, session_id))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error updating session {session_id}: {e}")

def generate_keys():
    """Generate RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_pem, public_pem

def register_user(user_id, nickname):
    """Register a user with nickname and generate keys."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        private_key, public_key = generate_keys()
        logger.info(f"Generated keys for user {user_id}: public_key starts with {public_key[:50]}...")

        cursor.execute('''
            UPDATE users SET nickname = ?, public_key = ?, private_key = ?, registration_status = 'registered'
            WHERE id = ?
        ''', (nickname, public_key, private_key, user_id))

        logger.info(f"Updated user {user_id} with keys and status 'registered'")

        conn.commit()
        conn.close()
        return public_key
    except sqlite3.Error as e:
        logger.error(f"Error registering user {user_id}: {e}")
        return None

def get_user(user_id):
    """Get user data by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_dict = dict(row)
        logger.info(f"Retrieved user {user_id}: nickname={user_dict.get('nickname')}, public_key={user_dict.get('public_key')[:50] if user_dict.get('public_key') else None}, status={user_dict.get('registration_status')}")
        return user_dict
    else:
        logger.info(f"User {user_id} not found")
        return None

def insert_pending_message(recipient_id, sender_id, text):
    """Insert a pending message."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO pending_messages (recipient_id, sender_id, text, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (recipient_id, sender_id, text, datetime.datetime.now()))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error inserting pending message: {e}")

def get_pending_messages_for_user(user_id):
    """Get pending messages for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM pending_messages
        WHERE recipient_id = ? AND delivered = FALSE
        ORDER BY timestamp ASC
    ''', (user_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_pending_message_delivered(message_id):
    """Mark a pending message as delivered."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE pending_messages SET delivered = TRUE WHERE id = ?
        ''', (message_id,))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error marking message delivered: {e}")

def get_messages_for_user(user_id, limit=50):
    """Get recent messages for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM messages
        WHERE sender_id = ? OR receiver_id = ? OR receiver_id = 'all'
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (user_id, user_id, limit))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Admin functions

def create_admin_user(username, email, hashed_password, role='admin'):
    """Create a new admin user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO admin_users (username, email, hashed_password, role)
            VALUES (?, ?, ?, ?)
        ''', (username, email, hashed_password, role))

        admin_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return admin_id
    except sqlite3.Error as e:
        logger.error(f"Error creating admin user {username}: {e}")
        return None

def get_admin_user_by_username(username):
    """Get admin user by username."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM admin_users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_dict = dict(row)
        return user_dict
    else:
        return None

def get_admin_user_by_id(admin_id):
    """Get admin user by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM admin_users WHERE id = ?', (admin_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_role_permissions(role_name):
    """Get permissions for a role."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT permissions FROM roles WHERE name = ?', (role_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        import json
        return json.loads(row['permissions'])
    return []

def update_admin_last_login(admin_id):
    """Update admin user's last login time."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE admin_users SET last_login = ? WHERE id = ?
        ''', (datetime.datetime.now(), admin_id))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error updating last login for admin {admin_id}: {e}")

def get_all_users(limit=100, offset=0):
    """Get all users with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM users
        ORDER BY last_seen DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_messages(limit=100, offset=0):
    """Get all messages with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM messages
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_sessions(limit=100, offset=0):
    """Get all sessions with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM sessions
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def log_audit(admin_user_id, action, resource, resource_id=None, details=None, ip_address=None):
    """Log an audit event."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO audit_logs (admin_user_id, action, resource, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (admin_user_id, action, resource, resource_id, details, ip_address))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error logging audit: {e}")

def get_audit_logs(limit=100, offset=0):
    """Get audit logs with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT al.*, au.username
        FROM audit_logs al
        LEFT JOIN admin_users au ON al.admin_user_id = au.id
        ORDER BY al.timestamp DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_bot_stats():
    """Get bot statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Get user count
    cursor.execute('SELECT COUNT(*) as user_count FROM users')
    user_count = cursor.fetchone()['user_count']

    # Get message count
    cursor.execute('SELECT COUNT(*) as message_count FROM messages')
    message_count = cursor.fetchone()['message_count']

    # Get active sessions
    cursor.execute('SELECT COUNT(*) as active_sessions FROM sessions WHERE end_time IS NULL')
    active_sessions = cursor.fetchone()['active_sessions']

    # Get registered users
    cursor.execute("SELECT COUNT(*) as registered_users FROM users WHERE registration_status = 'registered'")
    registered_users = cursor.fetchone()['registered_users']

    conn.close()
    return {
        'total_users': user_count,
        'total_messages': message_count,
        'active_sessions': active_sessions,
        'registered_users': registered_users
    }

# Geolocation Database Functions

# Zone Management Functions
def create_zone(name, description, center_latitude, center_longitude, radius_meters, zone_type='circular', coordinates=None, created_by=None):
    """Create a new zone."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO zones (name, description, center_latitude, center_longitude, radius_meters, zone_type, coordinates, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, center_latitude, center_longitude, radius_meters, zone_type, coordinates, created_by))

        zone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return zone_id
    except sqlite3.Error as e:
        logger.error(f"Error creating zone {name}: {e}")
        return None

def get_zone(zone_id):
    """Get zone by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT z.*, a.username as created_by_username
        FROM zones z
        LEFT JOIN admin_users a ON z.created_by = a.id
        WHERE z.id = ?
    ''', (zone_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_zones(limit=100, offset=0):
    """Get all zones with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT z.*, a.username as created_by_username
        FROM zones z
        LEFT JOIN admin_users a ON z.created_by = a.id
        WHERE z.is_active = TRUE
        ORDER BY z.created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_zone(zone_id, **kwargs):
    """Update zone fields."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Build dynamic update query
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['name', 'description', 'center_latitude', 'center_longitude', 'radius_meters', 'zone_type', 'coordinates', 'is_active']:
                fields.append(f"{key} = ?")
                values.append(value)

        if not fields:
            return False

        values.append(zone_id)
        query = f"UPDATE zones SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
        values.append(datetime.datetime.now())

        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating zone {zone_id}: {e}")
        return False

def delete_zone(zone_id):
    """Soft delete zone by setting is_active to FALSE."""
    return update_zone(zone_id, is_active=False)

# User Group Management Functions
def create_user_group(name, description, created_by=None):
    """Create a new user group."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO user_groups (name, description, created_by)
            VALUES (?, ?, ?)
        ''', (name, description, created_by))

        group_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return group_id
    except sqlite3.Error as e:
        logger.error(f"Error creating user group {name}: {e}")
        return None

def get_user_group(group_id):
    """Get user group by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM user_groups WHERE id = ?', (group_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_user_groups(limit=100, offset=0):
    """Get all user groups with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT ug.*, a.username as created_by_username
        FROM user_groups ug
        LEFT JOIN admin_users a ON ug.created_by = a.id
        ORDER BY ug.created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_user_to_group(user_id, group_id, added_by=None):
    """Add user to group."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR IGNORE INTO user_group_members (user_id, group_id, added_by)
            VALUES (?, ?, ?)
        ''', (user_id, group_id, added_by))

        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error adding user {user_id} to group {group_id}: {e}")
        return False

def remove_user_from_group(user_id, group_id):
    """Remove user from group."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM user_group_members WHERE user_id = ? AND group_id = ?', (user_id, group_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error removing user {user_id} from group {group_id}: {e}")
        return False

def get_users_in_group(group_id):
    """Get all users in a group."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.* FROM users u
        INNER JOIN user_group_members ugm ON u.id = ugm.user_id
        WHERE ugm.group_id = ?
        ORDER BY u.last_seen DESC
    ''', (group_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Alert Management Functions
def create_alert(user_id, zone_id, alert_type, title, message, severity='medium', location_latitude=None, location_longitude=None):
    """Create a new alert."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alerts (user_id, zone_id, alert_type, severity, title, message, location_latitude, location_longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, zone_id, alert_type, severity, title, message, location_latitude, location_longitude))

        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return alert_id
    except sqlite3.Error as e:
        logger.error(f"Error creating alert: {e}")
        return None

def get_alert(alert_id):
    """Get alert by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM alerts WHERE id = ?', (alert_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_alerts(limit=100, offset=0, include_acknowledged=False):
    """Get all alerts with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    if not include_acknowledged:
        cursor.execute('''
            SELECT a.*, u.long_name as user_name, z.name as zone_name, au.username as acknowledged_by_username
            FROM alerts a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN zones z ON a.zone_id = z.id
            LEFT JOIN admin_users au ON a.acknowledged_by = au.id
            WHERE a.is_acknowledged = FALSE
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
    else:
        cursor.execute('''
            SELECT a.*, u.long_name as user_name, z.name as zone_name, au.username as acknowledged_by_username
            FROM alerts a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN zones z ON a.zone_id = z.id
            LEFT JOIN admin_users au ON a.acknowledged_by = au.id
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def acknowledge_alert(alert_id, acknowledged_by):
    """Acknowledge an alert."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE alerts SET is_acknowledged = TRUE, acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        ''', (acknowledged_by, datetime.datetime.now(), alert_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        return False

def resolve_alert(alert_id, resolved_by):
    """Resolve an alert."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE alerts SET is_resolved = TRUE, resolved_by = ?, resolved_at = ?
            WHERE id = ?
        ''', (resolved_by, datetime.datetime.now(), alert_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        return False

# Alert Rules Management Functions
def create_alert_rule(name, description, alert_type, severity='medium', zone_id=None, conditions=None, target_groups=None, escalation_rules=None, created_by=None):
    """Create a new alert rule."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alert_rules (name, description, alert_type, severity, zone_id, conditions, target_groups, escalation_rules, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, alert_type, severity, zone_id, conditions, target_groups, escalation_rules, created_by))

        rule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return rule_id
    except sqlite3.Error as e:
        logger.error(f"Error creating alert rule {name}: {e}")
        return None

def get_alert_rule(rule_id):
    """Get alert rule by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT ar.*, z.name as zone_name, au.username as created_by_username
        FROM alert_rules ar
        LEFT JOIN zones z ON ar.zone_id = z.id
        LEFT JOIN admin_users au ON ar.created_by = au.id
        WHERE ar.id = ?
    ''', (rule_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_alert_rules(limit=100, offset=0, active_only=True):
    """Get all alert rules with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT ar.*, z.name as zone_name, au.username as created_by_username
        FROM alert_rules ar
        LEFT JOIN zones z ON ar.zone_id = z.id
        LEFT JOIN admin_users au ON ar.created_by = au.id
    '''
    params = []

    if active_only:
        query += ' WHERE ar.is_active = TRUE'
        params.append(True)

    query += ' ORDER BY ar.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_alert_rule(rule_id, **kwargs):
    """Update alert rule fields."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        valid_fields = ['name', 'description', 'alert_type', 'severity', 'zone_id', 'conditions', 'target_groups', 'escalation_rules', 'is_active']
        for key, value in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return False

        values.append(rule_id)
        query = f"UPDATE alert_rules SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
        values.append(datetime.datetime.now())

        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating alert rule {rule_id}: {e}")
        return False

def delete_alert_rule(rule_id):
    """Soft delete alert rule by setting is_active to FALSE."""
    return update_alert_rule(rule_id, is_active=False)

# Location History Functions
def insert_location_history(user_id, latitude, longitude, altitude=None, accuracy=None, speed=None, heading=None, battery_level=None, is_moving=False):
    """Insert location data into history."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO location_history (user_id, latitude, longitude, altitude, accuracy, speed, heading, battery_level, is_moving)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, latitude, longitude, altitude, accuracy, speed, heading, battery_level, is_moving))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error inserting location history for {user_id}: {e}")
        return False

def get_location_history(user_id, limit=100, offset=0, start_time=None, end_time=None):
    """Get location history for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT * FROM location_history
        WHERE user_id = ?
    '''
    params = [user_id]

    if start_time:
        query += ' AND recorded_at >= ?'
        params.append(start_time)
    if end_time:
        query += ' AND recorded_at <= ?'
        params.append(end_time)

    query += ' ORDER BY recorded_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def cleanup_old_location_history(days_to_keep=30):
    """Clean up old location history data."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        cursor.execute('DELETE FROM location_history WHERE recorded_at < ?', (cutoff_date,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Cleaned up {deleted_count} old location history records")
        return deleted_count
    except sqlite3.Error as e:
        logger.error(f"Error cleaning up location history: {e}")
        return 0

# Location Cache Functions (for offline support)
def insert_location_cache(user_id, latitude, longitude, altitude=None, accuracy=None, speed=None, heading=None, battery_level=None):
    """Insert location data into cache for offline sync."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO location_cache (user_id, latitude, longitude, altitude, accuracy, speed, heading, battery_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, latitude, longitude, altitude, accuracy, speed, heading, battery_level))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error inserting location cache for {user_id}: {e}")
        return False

def get_unsynced_location_cache(limit=100):
    """Get unsynced location cache entries."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM location_cache
        WHERE synced = FALSE
        ORDER BY recorded_at ASC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_location_cache_synced(cache_ids):
    """Mark location cache entries as synced."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        current_time = datetime.datetime.now()
        cursor.execute(f'''
            UPDATE location_cache SET synced = TRUE, synced_at = ? WHERE id IN ({','.join(['?'] * len(cache_ids))})
        ''', [current_time] + cache_ids)

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error marking location cache as synced: {e}")
        return False

# User Geolocation Functions
def update_user_location(user_id, latitude, longitude, altitude=None, battery_level=None, device_status='online'):
    """Update user's current location and related fields."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET latitude = ?, longitude = ?, altitude = ?, battery_level = ?, device_status = ?, last_location_update = ?
            WHERE id = ?
        ''', (latitude, longitude, altitude, battery_level, device_status, datetime.datetime.now(), user_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating user location for {user_id}: {e}")
        return False

def update_user_tracking_settings(user_id, tracking_enabled=None, tracking_interval_active=None, tracking_interval_stationary=None):
    """Update user's tracking settings."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if tracking_enabled is not None:
            updates.append("tracking_enabled = ?")
            params.append(tracking_enabled)
        if tracking_interval_active is not None:
            updates.append("tracking_interval_active = ?")
            params.append(tracking_interval_active)
        if tracking_interval_stationary is not None:
            updates.append("tracking_interval_stationary = ?")
            params.append(tracking_interval_stationary)

        if not updates:
            return False

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating tracking settings for {user_id}: {e}")
        return False

def get_users_by_zone(zone_id):
    """Get all users currently in a specific zone."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM users WHERE current_zone_id = ? AND tracking_enabled = TRUE
        ORDER BY last_location_update DESC
    ''', (zone_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def check_user_in_zone(user_id, zone_id):
    """Check if user is currently in a zone using point-in-circle calculation."""
    # This is a simplified version - in production you'd want more sophisticated GIS calculations
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.latitude, u.longitude, z.center_latitude, z.center_longitude, z.radius_meters
        FROM users u, zones z
        WHERE u.id = ? AND z.id = ? AND u.current_zone_id = z.id
    ''', (user_id, zone_id))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    # Simple distance calculation (Haversine formula would be more accurate)
    user_lat, user_lon, center_lat, center_lon, radius = row
    distance = ((user_lat - center_lat) ** 2 + (user_lon - center_lon) ** 2) ** 0.5 * 111000  # Rough meters

    return distance <= radius

# Bot Trigger Management Functions
def create_trigger(name, description, trigger_type, trigger_config, conditions=None, priority=0, cooldown_seconds=0, created_by=None):
    """Create a new bot trigger."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO bot_triggers (name, description, trigger_type, trigger_config, conditions, priority, cooldown_seconds, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, trigger_type, trigger_config, conditions, priority, cooldown_seconds, created_by))

        trigger_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trigger_id
    except sqlite3.Error as e:
        logger.error(f"Error creating trigger {name}: {e}")
        return None

def get_trigger(trigger_id):
    """Get trigger by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT bt.*, a.username as created_by_username
        FROM bot_triggers bt
        LEFT JOIN admin_users a ON bt.created_by = a.id
        WHERE bt.id = ?
    ''', (trigger_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_triggers(limit=100, offset=0, active_only=True):
    """Get all triggers with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT bt.*, a.username as created_by_username
        FROM bot_triggers bt
        LEFT JOIN admin_users a ON bt.created_by = a.id
    '''
    params = []

    if active_only:
        query += ' WHERE bt.is_active = TRUE'
        params.append(True)

    query += ' ORDER BY bt.priority DESC, bt.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_trigger(trigger_id, **kwargs):
    """Update trigger fields."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        valid_fields = ['name', 'description', 'trigger_type', 'trigger_config', 'conditions', 'priority', 'is_active', 'cooldown_seconds']
        for key, value in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return False

        values.append(trigger_id)
        query = f"UPDATE bot_triggers SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
        values.append(datetime.datetime.now())

        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating trigger {trigger_id}: {e}")
        return False

def delete_trigger(trigger_id):
    """Soft delete trigger by setting is_active to FALSE."""
    return update_trigger(trigger_id, is_active=False)

def increment_trigger_count(trigger_id):
    """Increment trigger usage count."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE bot_triggers SET trigger_count = trigger_count + 1, last_triggered = ? WHERE id = ?
        ''', (datetime.datetime.now(), trigger_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error incrementing trigger count for {trigger_id}: {e}")
        return False

def log_trigger_execution(trigger_id, user_id, message_text, trigger_data, matched_conditions, executed_responses, execution_time_ms, success=True, error_message=None):
    """Log trigger execution."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO bot_trigger_logs (trigger_id, user_id, message_text, trigger_data, matched_conditions, executed_responses, execution_time_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trigger_id, user_id, message_text, trigger_data, matched_conditions, executed_responses, execution_time_ms, success, error_message))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    except sqlite3.Error as e:
        logger.error(f"Error logging trigger execution: {e}")
        return None

# Bot Response Management Functions
def create_response(name, description, response_type, content, variables=None, language='en', target_type='all', target_ids=None, channels=None, priority=0, created_by=None):
    """Create a new bot response."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO bot_responses (name, description, response_type, content, variables, language, target_type, target_ids, channels, priority, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, response_type, content, variables, language, target_type, target_ids, channels, priority, created_by))

        response_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return response_id
    except sqlite3.Error as e:
        logger.error(f"Error creating response {name}: {e}")
        return None

def get_response(response_id):
    """Get response by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT br.*, a.username as created_by_username
        FROM bot_responses br
        LEFT JOIN admin_users a ON br.created_by = a.id
        WHERE br.id = ?
    ''', (response_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_responses(limit=100, offset=0, active_only=True):
    """Get all responses with pagination."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT br.*, a.username as created_by_username
        FROM bot_responses br
        LEFT JOIN admin_users a ON br.created_by = a.id
    '''
    params = []

    if active_only:
        query += ' WHERE br.is_active = TRUE'
        params.append(True)

    query += ' ORDER BY br.priority DESC, br.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_response(response_id, **kwargs):
    """Update response fields."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        valid_fields = ['name', 'description', 'response_type', 'content', 'variables', 'language', 'target_type', 'target_ids', 'channels', 'priority', 'is_active']
        for key, value in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return False

        values.append(response_id)
        query = f"UPDATE bot_responses SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
        values.append(datetime.datetime.now())

        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating response {response_id}: {e}")
        return False

def delete_response(response_id):
    """Soft delete response by setting is_active to FALSE."""
    return update_response(response_id, is_active=False)

def increment_response_usage(response_id):
    """Increment response usage count."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE bot_responses SET usage_count = usage_count + 1 WHERE id = ?', (response_id,))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error incrementing response usage for {response_id}: {e}")
        return False

def log_response_delivery(response_id, trigger_log_id, user_id, channel, content, delivery_status='sent', delivery_time_ms=None, error_message=None):
    """Log response delivery."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO bot_response_logs (response_id, trigger_log_id, user_id, channel, content, delivery_status, delivery_time_ms, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (response_id, trigger_log_id, user_id, channel, content, delivery_status, delivery_time_ms, error_message))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error logging response delivery: {e}")
        return False

def get_responses_for_trigger(trigger_id):
    """Get all active responses that could be triggered by a specific trigger."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM bot_responses
        WHERE is_active = TRUE
        ORDER BY priority DESC, created_at ASC
    ''')

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_trigger_logs(trigger_id=None, limit=100, offset=0):
    """Get trigger execution logs."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT btl.*, bt.name as trigger_name, u.long_name as user_name
        FROM bot_trigger_logs btl
        LEFT JOIN bot_triggers bt ON btl.trigger_id = bt.id
        LEFT JOIN users u ON btl.user_id = u.id
    '''
    params = []

    if trigger_id:
        query += ' WHERE btl.trigger_id = ?'
        params.append(trigger_id)

    query += ' ORDER BY btl.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_response_logs(response_id=None, limit=100, offset=0):
    """Get response delivery logs."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT brl.*, br.name as response_name, u.long_name as user_name
        FROM bot_response_logs brl
        LEFT JOIN bot_responses br ON brl.response_id = br.id
        LEFT JOIN users u ON brl.user_id = u.id
    '''
    params = []

    if response_id:
        query += ' WHERE brl.response_id = ?'
        params.append(response_id)

    query += ' ORDER BY brl.created_at DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Message Chunk Management Functions

def insert_message_chunk(message_id, sender_id, receiver_id, chunk_number, total_chunks, content, status='pending', sent_at=None, confirmed_at=None, retry_count=0):
    """Insert a message chunk."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO message_chunks (message_id, sender_id, receiver_id, chunk_number, total_chunks, content, status, sent_at, confirmed_at, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (message_id, sender_id, receiver_id, chunk_number, total_chunks, content, status, sent_at, confirmed_at, retry_count))

        chunk_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chunk_id
    except sqlite3.Error as e:
        logger.error(f"Error inserting message chunk for message {message_id}: {e}")
        return None

def get_message_chunks(message_id):
    """Get all chunks for a message."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM message_chunks
        WHERE message_id = ?
        ORDER BY chunk_number ASC
    ''', (message_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_message_chunks(message_id):
    """Delete all chunks for a message."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM message_chunks WHERE message_id = ?', (message_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error deleting message chunks for message {message_id}: {e}")
        return False

# Message Delivery Status Management Functions

def insert_delivery_status(message_id, sender_id, receiver_id, total_chunks, status='in_progress'):
    """Insert delivery status for a message."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO message_delivery_status (message_id, sender_id, receiver_id, total_chunks, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (message_id, sender_id, receiver_id, total_chunks, status))

        delivery_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return delivery_id
    except sqlite3.Error as e:
        logger.error(f"Error inserting delivery status for message {message_id}: {e}")
        return None

def update_delivery_status(delivery_id, status=None, completed_at=None, last_activity=None, delivered_chunks=None):
    """Update delivery status."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if completed_at is not None:
            updates.append("completed_at = ?")
            values.append(completed_at)
        if last_activity is not None:
            updates.append("last_activity = ?")
            values.append(last_activity)
        if delivered_chunks is not None:
            updates.append("delivered_chunks = ?")
            values.append(delivered_chunks)

        if not updates:
            return False

        values.append(delivery_id)

        query = f"UPDATE message_delivery_status SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating delivery status {delivery_id}: {e}")
        return False

def get_delivery_status_for_message(message_id):
    """Get delivery status for a message."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT mds.*, u.long_name as sender_name, ur.long_name as receiver_name
        FROM message_delivery_status mds
        LEFT JOIN users u ON mds.sender_id = u.id
        LEFT JOIN users ur ON mds.receiver_id = ur.id
        WHERE mds.message_id = ?
        ORDER BY mds.started_at ASC
    ''', (message_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_chunks_for_message(message_id):
    """Get all chunks for a message."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT mc.*, u.long_name as sender_name, ur.long_name as receiver_name
        FROM message_chunks mc
        LEFT JOIN users u ON mc.sender_id = u.id
        LEFT JOIN users ur ON mc.receiver_id = ur.id
        WHERE mc.message_id = ?
        ORDER BY mc.chunk_number ASC
    ''', (message_id,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_pending_chunks_for_recipient(recipient_id, limit=50):
    """Get pending chunks for a recipient."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT mc.*, u.long_name as sender_name
        FROM message_chunks mc
        LEFT JOIN users u ON mc.sender_id = u.id
        WHERE mc.receiver_id = ? AND mc.status IN ('pending', 'sent')
        ORDER BY mc.created_at ASC, mc.chunk_number ASC
        LIMIT ?
    ''', (recipient_id, limit))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_chunk_delivered(chunk_id, confirmed_at=None):
    """Mark a chunk as delivered."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if confirmed_at is None:
            confirmed_at = datetime.datetime.now()

        cursor.execute('''
            UPDATE message_chunks SET status = 'delivered', confirmed_at = ? WHERE id = ?
        ''', (confirmed_at, chunk_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error marking chunk {chunk_id} as delivered: {e}")
        return False

def mark_chunk_failed(chunk_id, error_message=None):
    """Mark a chunk as failed."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE message_chunks SET status = 'failed' WHERE id = ?
        ''', (chunk_id,))

        # Log the error if provided
        if error_message:
            logger.error(f"Chunk {chunk_id} failed: {error_message}")

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error marking chunk {chunk_id} as failed: {e}")
        return False

def mark_chunk_sent(chunk_id, sent_at=None):
    """Mark a chunk as sent."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if sent_at is None:
            sent_at = datetime.datetime.now()

        cursor.execute('''
            UPDATE message_chunks SET status = 'sent', sent_at = ? WHERE id = ?
        ''', (sent_at, chunk_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error marking chunk {chunk_id} as sent: {e}")
        return False

def increment_delivered_chunks(delivery_id):
    """Increment delivered chunks count for a message delivery."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE message_delivery_status
            SET delivered_chunks = delivered_chunks + 1, last_activity = ?
            WHERE id = ?
        ''', (datetime.datetime.now(), delivery_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error incrementing delivered chunks for delivery {delivery_id}: {e}")
        return False

def complete_message_delivery(delivery_id, completed_at=None):
    """Mark message delivery as completed."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if completed_at is None:
            completed_at = datetime.datetime.now()

        cursor.execute('''
            UPDATE message_delivery_status
            SET status = 'completed', completed_at = ?, last_activity = ?
            WHERE id = ?
        ''', (completed_at, datetime.datetime.now(), delivery_id))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error completing delivery {delivery_id}: {e}")
        return False

def increment_chunk_retry_count(chunk_id):
    """Increment retry count for a chunk."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE message_chunks
            SET retry_count = retry_count + 1
            WHERE id = ?
        ''', (chunk_id,))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error incrementing retry count for chunk {chunk_id}: {e}")
        return False

def get_failed_chunks(limit=100, offset=0):
    """Get failed chunks for retry."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT mc.*, u.long_name as sender_name, ur.long_name as receiver_name
        FROM message_chunks mc
        LEFT JOIN users u ON mc.sender_id = u.id
        LEFT JOIN users ur ON mc.receiver_id = ur.id
        WHERE mc.status = 'failed' AND mc.retry_count < 3
        ORDER BY mc.created_at ASC
        LIMIT ? OFFSET ?
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Analytics Database Functions

def get_user_stats():
    """Get comprehensive user statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total users
    cursor.execute('SELECT COUNT(*) as total FROM users')
    total_users = cursor.fetchone()['total']

    # Active today (users with activity in last 24 hours)
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    cursor.execute('SELECT COUNT(DISTINCT user_id) as active FROM location_history WHERE recorded_at > ?', (yesterday,))
    active_today = cursor.fetchone()['active']

    # Online now (users with recent activity in last 5 minutes)
    five_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
    cursor.execute('SELECT COUNT(*) as online FROM users WHERE last_location_update > ?', (five_minutes_ago,))
    online_now = cursor.fetchone()['online']

    conn.close()
    return {
        'total_users': total_users,
        'active_today': active_today,
        'online_now': online_now
    }

def get_message_stats():
    """Get message statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total messages
    cursor.execute('SELECT COUNT(*) as total FROM messages')
    total_messages = cursor.fetchone()['total']

    # Messages today
    today = datetime.datetime.now().date()
    cursor.execute('SELECT COUNT(*) as today FROM messages WHERE DATE(timestamp) = ?', (today,))
    messages_today = cursor.fetchone()['today']

    # Messages this week
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    cursor.execute('SELECT COUNT(*) as week FROM messages WHERE timestamp > ?', (week_ago,))
    messages_week = cursor.fetchone()['week']

    # Bot responses
    cursor.execute('SELECT COUNT(*) as bot_responses FROM messages WHERE sender_id LIKE "bot_%"')
    bot_responses = cursor.fetchone()['bot_responses']

    conn.close()
    return {
        'total': total_messages,
        'today': messages_today,
        'week': messages_week,
        'bot_responses': bot_responses
    }

def get_alert_stats():
    """Get alert statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total alerts
    cursor.execute('SELECT COUNT(*) as total FROM alerts')
    total_alerts = cursor.fetchone()['total']

    # Active alerts
    cursor.execute('SELECT COUNT(*) as active FROM alerts WHERE is_acknowledged = FALSE')
    active_alerts = cursor.fetchone()['active']

    # Critical alerts
    cursor.execute('SELECT COUNT(*) as critical FROM alerts WHERE severity = "critical" AND is_acknowledged = FALSE')
    critical_alerts = cursor.fetchone()['critical']

    # Resolved today
    today = datetime.datetime.now().date()
    cursor.execute('SELECT COUNT(*) as resolved_today FROM alerts WHERE DATE(resolved_at) = ? AND is_resolved = TRUE', (today,))
    resolved_today = cursor.fetchone()['resolved_today']

    conn.close()
    return {
        'total': total_alerts,
        'active': active_alerts,
        'critical': critical_alerts,
        'resolved_today': resolved_today
    }

def get_zone_stats():
    """Get zone statistics."""
    logger.info("get_zone_stats called")
    conn = get_connection()
    cursor = conn.cursor()

    # Total zones
    cursor.execute('SELECT COUNT(*) as total FROM zones WHERE is_active = TRUE')
    total_zones = cursor.fetchone()['total']
    logger.info(f"Total zones: {total_zones} (type: {type(total_zones)})")

    # Active zones
    cursor.execute('SELECT COUNT(*) as active FROM zones WHERE is_active = TRUE')
    active_zones = cursor.fetchone()['active']
    logger.info(f"Active zones: {active_zones} (type: {type(active_zones)})")

    # Average users per zone
    cursor.execute('''
        SELECT AVG(user_count) as avg_users
        FROM (
            SELECT COUNT(u.id) as user_count
            FROM zones z
            LEFT JOIN users u ON z.id = u.current_zone_id
            WHERE z.is_active = TRUE
            GROUP BY z.id
        )
    ''')
    avg_users_result = cursor.fetchone()
    avg_users = avg_users_result['avg_users'] or 0
    logger.info(f"Avg users result: {avg_users_result}, avg_users: {avg_users} (type: {type(avg_users)})")

    conn.close()

    result = {
        'total': total_zones,
        'active': active_zones,
        'avg_users_per_zone': round(avg_users, 2)
    }
    logger.info(f"Returning zone stats: {result}")
    return result

def get_process_stats():
    """Get process statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total processes
    cursor.execute('SELECT COUNT(*) as total FROM processes WHERE is_active = TRUE')
    total_processes = cursor.fetchone()['total']

    # Running processes
    cursor.execute('SELECT COUNT(*) as running FROM process_executions WHERE status = "running"')
    running_processes = cursor.fetchone()['running']

    # Completed today
    today = datetime.datetime.now().date()
    cursor.execute('SELECT COUNT(*) as completed_today FROM process_executions WHERE DATE(completed_at) = ? AND status = "completed"', (today,))
    completed_today = cursor.fetchone()['completed_today']

    conn.close()
    return {
        'total': total_processes,
        'running': running_processes,
        'completed_today': completed_today
    }

def get_message_count_for_date(date):
    """Get message count for a specific date."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as count FROM messages WHERE DATE(timestamp) = ?', (date,))
    count = cursor.fetchone()['count']

    conn.close()
    return count

def get_alert_count_for_date(date):
    """Get alert count for a specific date."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE DATE(created_at) = ?', (date,))
    count = cursor.fetchone()['count']

    conn.close()
    return count

def get_active_user_count_for_date(date):
    """Get active user count for a specific date."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(DISTINCT user_id) as count FROM location_history WHERE DATE(recorded_at) = ?', (date,))
    count = cursor.fetchone()['count']

    conn.close()
    return count

# Additional analytics functions for detailed reports

def get_user_registration_trends(start_date):
    """Get user registration trends over time."""
    logger.info(f"get_user_registration_trends called with start_date: {start_date}")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM users
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    logger.info(f"get_user_registration_trends returned {len(rows)} rows")
    return [{'date': row['date'], 'count': row['count']} for row in rows]

def get_user_activity_patterns(days):
    """Get user activity patterns."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT strftime('%H', recorded_at) as hour, COUNT(*) as activity_count
        FROM location_history
        WHERE recorded_at >= ?
        GROUP BY hour
        ORDER BY hour
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'hour': int(row['hour']), 'activity_count': row['activity_count']} for row in rows]

def get_user_geographic_distribution():
    """Get geographic distribution of users."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            ROUND(latitude, 1) as lat_bin,
            ROUND(longitude, 1) as lon_bin,
            COUNT(*) as user_count
        FROM users
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        GROUP BY lat_bin, lon_bin
        ORDER BY user_count DESC
        LIMIT 100
    ''')

    rows = cursor.fetchall()
    conn.close()
    return [{'lat': row['lat_bin'], 'lon': row['lon_bin'], 'count': row['user_count']} for row in rows]

def get_user_device_stats():
    """Get user device statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT device_status, COUNT(*) as count
        FROM users
        GROUP BY device_status
    ''')

    rows = cursor.fetchall()
    conn.close()
    return {row['device_status'] or 'unknown': row['count'] for row in rows}

def get_message_volume_trends(start_date):
    """Get message volume trends."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM messages
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'date': row['date'], 'count': row['count']} for row in rows]

def get_message_type_distribution(days):
    """Get message type distribution."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT direction, COUNT(*) as count
        FROM messages
        WHERE timestamp >= ?
        GROUP BY direction
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return {row['direction']: row['count'] for row in rows}

def get_message_response_times(days):
    """Get message response time analytics."""
    # This would require more complex logic to match sent/received messages
    # For now, return basic stats
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT AVG(execution_time_ms) as avg_response_time, COUNT(*) as total_responses
        FROM bot_trigger_logs
        WHERE created_at >= ?
    ''', (start_date,))

    row = cursor.fetchone()
    conn.close()

    return {
        'avg_response_time': row['avg_response_time'] or 0,
        'total_responses': row['total_responses'] or 0
    }

def get_message_peak_times(days):
    """Get message peak usage times."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as message_count
        FROM messages
        WHERE timestamp >= ?
        GROUP BY hour
        ORDER BY message_count DESC
        LIMIT 5
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'hour': int(row['hour']), 'count': row['message_count']} for row in rows]

def get_bot_interaction_quality(days):
    """Get bot interaction quality metrics."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT
            AVG(execution_time_ms) as avg_response_time,
            COUNT(CASE WHEN success = 1 THEN 1 END) as successful_interactions,
            COUNT(*) as total_interactions
        FROM bot_trigger_logs
        WHERE created_at >= ?
    ''', (start_date,))

    row = cursor.fetchone()
    conn.close()

    total = row['total_interactions'] or 0
    successful = row['successful_interactions'] or 0

    return {
        'avg_response_time': row['avg_response_time'] or 0,
        'success_rate': (successful / total * 100) if total > 0 else 0,
        'total_interactions': total
    }

def get_alert_trends(start_date):
    """Get alert trends over time."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM alerts
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'date': row['date'], 'count': row['count']} for row in rows]

def get_alert_type_distribution(days):
    """Get alert type distribution."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT alert_type, COUNT(*) as count
        FROM alerts
        WHERE created_at >= ?
        GROUP BY alert_type
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return {row['alert_type']: row['count'] for row in rows}

def get_alert_response_times(days):
    """Get alert response time analytics."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT AVG(julianday(acknowledged_at) - julianday(created_at)) * 24 * 60 as avg_response_minutes
        FROM alerts
        WHERE created_at >= ? AND acknowledged_at IS NOT NULL
    ''', (start_date,))

    row = cursor.fetchone()
    conn.close()

    return {
        'avg_response_minutes': row['avg_response_minutes'] or 0
    }

def get_alert_false_positive_rate(days):
    """Get alert false positive rate."""
    # This would require manual classification of alerts
    # For now, return a placeholder
    return {
        'false_positive_rate': 0.05,  # 5% placeholder
        'total_analyzed': 100
    }

def get_zone_based_alerts(days):
    """Get alerts grouped by zone."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT z.name as zone_name, COUNT(a.id) as alert_count
        FROM alerts a
        LEFT JOIN zones z ON a.zone_id = z.id
        WHERE a.created_at >= ?
        GROUP BY z.id, z.name
        ORDER BY alert_count DESC
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'zone': row['zone_name'] or 'No Zone', 'count': row['alert_count']} for row in rows]

def get_movement_patterns(days):
    """Get movement patterns analytics."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT user_id, COUNT(*) as location_updates, AVG(speed) as avg_speed
        FROM location_history
        WHERE recorded_at >= ? AND speed IS NOT NULL
        GROUP BY user_id
        ORDER BY location_updates DESC
        LIMIT 50
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'user_id': row['user_id'], 'updates': row['location_updates'], 'avg_speed': row['avg_speed'] or 0} for row in rows]

def get_zone_dwell_times(days):
    """Get zone dwell time analytics."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT
            u.current_zone_id,
            z.name as zone_name,
            COUNT(DISTINCT u.id) as users_in_zone,
            AVG((julianday('now') - julianday(u.last_location_update)) * 24) as avg_dwell_hours
        FROM users u
        LEFT JOIN zones z ON u.current_zone_id = z.id
        WHERE u.last_location_update >= ?
        GROUP BY u.current_zone_id, z.name
        ORDER BY users_in_zone DESC
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{
        'zone_id': row['current_zone_id'],
        'zone_name': row['zone_name'] or 'No Zone',
        'users': row['users_in_zone'],
        'avg_dwell_hours': row['avg_dwell_hours'] or 0
    } for row in rows]

def get_location_heatmap_data(days):
    """Get location heatmap data."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT
            ROUND(latitude, 2) as lat,
            ROUND(longitude, 2) as lon,
            COUNT(*) as intensity
        FROM location_history
        WHERE recorded_at >= ?
        GROUP BY ROUND(latitude, 2), ROUND(longitude, 2)
        HAVING intensity > 1
        ORDER BY intensity DESC
        LIMIT 1000
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return [{'lat': row['lat'], 'lon': row['lon'], 'intensity': row['intensity']} for row in rows]

def get_location_predictions():
    """Get predictive analytics for locations."""
    # TODO: Implement actual predictive analytics with ML models
    logger.warning("get_location_predictions returning placeholder data - implement ML-based predictions")
    return {
        'predicted_movements': [],
        'risk_areas': [],
        'optimal_routes': []
    }

def get_speed_analysis(days):
    """Get speed analysis for users."""
    conn = get_connection()
    cursor = conn.cursor()

    start_date = datetime.datetime.now() - datetime.timedelta(days=days)

    cursor.execute('''
        SELECT
            CASE
                WHEN speed < 5 THEN 'walking'
                WHEN speed < 20 THEN 'cycling'
                WHEN speed < 60 THEN 'driving'
                ELSE 'high_speed'
            END as speed_category,
            COUNT(*) as count
        FROM location_history
        WHERE recorded_at >= ? AND speed IS NOT NULL
        GROUP BY speed_category
    ''', (start_date,))

    rows = cursor.fetchall()
    conn.close()
    return {row['speed_category']: row['count'] for row in rows}

def get_system_performance_metrics(days):
    """Get system performance metrics."""
    # TODO: Implement actual system performance monitoring
    logger.warning("get_system_performance_metrics returning placeholder data - implement actual monitoring")
    return {
        'cpu_usage': 45.2,
        'memory_usage': 67.8,
        'disk_usage': 23.1,
        'network_io': 150.5
    }

def get_api_response_times(days):
    """Get API response time metrics."""
    # TODO: Implement actual API response time monitoring
    logger.warning("get_api_response_times returning placeholder data - implement actual monitoring")
    return {
        'avg_response_time': 125.3,
        'p95_response_time': 450.0,
        'error_rate': 0.02
    }

def get_database_performance_metrics(days):
    """Get database performance metrics."""
    # TODO: Implement actual database performance monitoring
    logger.warning("get_database_performance_metrics returning placeholder data - implement actual monitoring")
    return {
        'query_count': 15420,
        'avg_query_time': 45.2,
        'slow_queries': 23,
        'connection_count': 12
    }

def get_websocket_metrics(days):
    """Get WebSocket connection metrics."""
    # TODO: Implement actual WebSocket monitoring
    logger.warning("get_websocket_metrics returning placeholder data - implement actual monitoring")
    return {
        'active_connections': 45,
        'messages_per_second': 12.3,
        'connection_drops': 5,
        'avg_session_duration': 1800
    }