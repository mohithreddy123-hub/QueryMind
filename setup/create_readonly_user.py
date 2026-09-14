import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mysql.connector
from config.settings import (
    MYSQL_ADMIN_HOST,
    MYSQL_ADMIN_PORT,
    MYSQL_ADMIN_USER,
    MYSQL_ADMIN_PASSWORD,
    MYSQL_DATABASE,
    MYSQL_USER,
    MYSQL_PASSWORD,
)

conn = mysql.connector.connect(
    host=MYSQL_ADMIN_HOST,
    port=MYSQL_ADMIN_PORT,
    user=MYSQL_ADMIN_USER,
    password=MYSQL_ADMIN_PASSWORD,
)
cursor = conn.cursor()

statements = [
    f"CREATE USER IF NOT EXISTS '{MYSQL_USER}'@'%' IDENTIFIED BY '{MYSQL_PASSWORD}'",
    f"GRANT SELECT ON {MYSQL_DATABASE}.* TO '{MYSQL_USER}'@'%'",
    "FLUSH PRIVILEGES",
]

for stmt in statements:
    cursor.execute(stmt)
    print(f"  OK: {stmt}")

conn.commit()
cursor.close()
conn.close()
print(f"\nRead-only user '{MYSQL_USER}' initialized successfully.")
