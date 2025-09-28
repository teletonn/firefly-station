import sqlite3

conn = sqlite3.connect('meshtastic_llm.db')
cursor = conn.cursor()

# Check admin users
cursor.execute('SELECT * FROM admin_users')
admins = cursor.fetchall()
print(f'Admin users: {len(admins)}')
for admin in admins:
    print(dict(zip([desc[0] for desc in cursor.description], admin)))

# Check roles
cursor.execute('SELECT * FROM roles')
roles = cursor.fetchall()
print(f'\nRoles: {len(roles)}')
for role in roles:
    print(dict(zip([desc[0] for desc in cursor.description], role)))

conn.close()