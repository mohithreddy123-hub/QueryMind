"""Temporary script to create the read-only MySQL user."""
import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="Root!@#$%12345",
)
cursor = conn.cursor()

statements = [
    "CREATE USER IF NOT EXISTS 'textsql_reader'@'localhost' IDENTIFIED BY 'Reader!@#$%12345'",
    "GRANT SELECT ON text_to_sql_db.* TO 'textsql_reader'@'localhost'",
    "FLUSH PRIVILEGES",
]

for stmt in statements:
    cursor.execute(stmt)
    print(f"  OK: {stmt}")

conn.commit()
cursor.close()
conn.close()
print("\nRead-only user 'textsql_reader' created successfully.")
