import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google import genai

from config.settings import GEMINI_API_KEY, GEMINI_MODEL


SQL_GENERATION_PROMPT = """\
You are an expert MySQL database assistant.

Your task is to write a single SQL SELECT query that answers the user's question
using the database schema provided below.

USER QUESTION:
{question}

RELEVANT DATABASE SCHEMA:
{schema}

STRICT RULES — follow all of them without exception:
1. Generate ONLY a single SQL SELECT query. Nothing else.
2. Use ONLY the tables and columns that appear in the schema above.
   Do not invent column names or tables that are not in the schema.
3. Do NOT generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE,
   REPLACE, or any other write/destructive operation.
4. Return ONLY the raw SQL query — no explanation, no comments, no markdown
   code fences (no ```sql or ```). Just the SQL.
5. Use valid MySQL 8.0 syntax.
6. Use table aliases (e.g. o for orders, p for products) when joining tables.
7. If the question asks for a "top N" result, include a LIMIT clause.
8. For revenue calculations, always filter payments WHERE status = 'paid'.
9. For time-based questions (this week, this month, last week, yesterday),
   use MySQL date functions: NOW(), DATE_SUB(), MONTH(), WEEK(), YEAR(), DATE().
10. If the question genuinely cannot be answered with the provided schema,
    respond with exactly: CANNOT_ANSWER
"""


def generate_sql(question: str, schema_text: str) -> dict:
    if not question or not question.strip():
        return {"success": False, "sql": "", "raw": "", "error": "Question cannot be empty."}

    if not schema_text or not schema_text.strip():
        return {"success": False, "sql": "", "raw": "", "error": "Schema context cannot be empty."}

    prompt = SQL_GENERATION_PROMPT.format(
        question=question.strip(),
        schema=schema_text.strip(),
    )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        raw_response = response.text.strip()
    except Exception as e:
        return {
            "success": False,
            "sql": "",
            "raw": "",
            "error": f"Gemini API error: {e}",
        }

    if raw_response.strip().upper() == "CANNOT_ANSWER":
        return {
            "success": False,
            "sql": "",
            "raw": raw_response,
            "error": (
                "The question cannot be answered using the available database schema. "
                "Try rephrasing your question or ask about something in the database."
            ),
        }

    sql = _extract_sql(raw_response)

    if not sql:
        return {
            "success": False,
            "sql": "",
            "raw": raw_response,
            "error": (
                f"Gemini returned a response but no SQL could be extracted. "
                f"Raw response: {raw_response[:300]}"
            ),
        }

    return {
        "success": True,
        "sql": sql,
        "raw": raw_response,
        "error": "",
    }


def _extract_sql(text: str) -> str:
    if not text:
        return ""

    fenced = re.search(r"```(?:sql)?\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    cleaned = text.strip()

    if re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        return cleaned

    select_match = re.search(r"(SELECT\b.*)", cleaned, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()

    return ""
