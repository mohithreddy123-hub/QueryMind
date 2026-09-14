import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


BLOCKED_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "MERGE",
    "CREATE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "FLUSH",
    "KILL",
    "SHUTDOWN",
    "LOAD_FILE",
    "INTO OUTFILE",
    "INTO DUMPFILE",
    "CALL",
    "EXEC",
    "EXECUTE",
    "/*!",
]

BLOCKED_PATTERNS = [
    r"\bUNION\b",
    r";\s*SELECT\b",
    r"--\s",
    r"/\*.*?\*/",
    r"\bSLEEP\s*\(",
    r"\bBENCHMARK\s*\(",
    r"\bINFORMATION_SCHEMA\b",
    r"\bMYSQL\.\w+",
]


def validate_sql(sql: str) -> dict:
    if not sql or len(sql.strip()) < 10:
        return {
            "valid": False,
            "reason": "SQL query is empty or too short to be valid.",
        }

    sql_stripped = sql.strip()

    if not re.match(r"^\s*SELECT\b", sql_stripped, re.IGNORECASE):
        first_word = sql_stripped.split()[0].upper() if sql_stripped.split() else "?"
        return {
            "valid": False,
            "reason": (
                f"Only SELECT queries are allowed. "
                f"The generated query starts with '{first_word}', which is not permitted."
            ),
        }

    sql_upper = sql_stripped.upper()
    for keyword in BLOCKED_KEYWORDS:
        if " " in keyword:
            if keyword in sql_upper:
                return {
                    "valid": False,
                    "reason": f"Blocked operation detected: '{keyword}'. Only SELECT queries are allowed.",
                }
        else:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, sql_upper):
                return {
                    "valid": False,
                    "reason": f"Blocked keyword detected: '{keyword}'. Only SELECT queries are allowed.",
                }

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, sql_stripped, re.IGNORECASE | re.DOTALL):
            match = re.search(pattern, sql_stripped, re.IGNORECASE | re.DOTALL)
            matched_text = match.group(0).strip() if match else pattern
            return {
                "valid": False,
                "reason": (
                    f"Potentially unsafe SQL pattern detected: '{matched_text[:50]}'. "
                    f"Query was blocked for security."
                ),
            }

    return {"valid": True, "reason": ""}
