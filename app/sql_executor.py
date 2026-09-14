import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mysql.connector
from mysql.connector import Error as MySQLError

from config.settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    MAX_RESULT_ROWS,
)


def execute_sql(sql: str) -> dict:
    connection = None
    cursor = None

    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connection_timeout=10,
        )

        cursor = connection.cursor(buffered=True)
        cursor.execute(sql)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        raw_rows = cursor.fetchall()
        total_row_count = len(raw_rows)

        truncated = total_row_count > MAX_RESULT_ROWS
        display_rows = raw_rows[:MAX_RESULT_ROWS]

        rows_as_dicts = [
            dict(zip(columns, row))
            for row in display_rows
        ]

        return {
            "success":   True,
            "columns":   columns,
            "rows":      rows_as_dicts,
            "row_count": total_row_count,
            "truncated": truncated,
            "error":     "",
        }

    except MySQLError as e:
        return {
            "success":   False,
            "columns":   [],
            "rows":      [],
            "row_count": 0,
            "truncated": False,
            "error":     f"MySQL error {e.errno}: {e.msg}",
        }

    except Exception as e:
        return {
            "success":   False,
            "columns":   [],
            "rows":      [],
            "row_count": 0,
            "truncated": False,
            "error":     f"Unexpected error during query execution: {e}",
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
