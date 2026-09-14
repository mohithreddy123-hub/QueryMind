import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google import genai

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

MAX_RESPONSE_ROWS = 20


RESPONSE_GENERATION_PROMPT = """\
You are a helpful data analyst assistant for an e-commerce business.

A user asked a question about the database, a SQL query was run, and the
results are shown below. Your job is to give the user a clear, concise,
natural-language answer.

USER QUESTION:
{question}

SQL QUERY THAT WAS EXECUTED:
{sql}

DATABASE RESULTS ({row_count} rows total, showing up to {max_rows}):
{results_text}

INSTRUCTIONS:
1. Answer the user's question directly and conversationally. Do not mention SQL.
2. If the result is a single number (count, sum, average), state it clearly.
   Format currency values in Indian Rupees with the ₹ symbol and proper
   comma formatting (e.g., ₹44,77,662.23).
3. If the result is a ranked list, present it as a numbered list.
4. If the result is empty (no rows), say "No results were found" and suggest
   why that might be (e.g., no data in that time period).
5. Keep the answer concise — 1 to 5 sentences for simple questions, a short
   list for ranking questions.
6. Do not mention the database, SQL, tables, or column names in your answer.
7. Do not make up data that isn't in the results. Only use what is shown.
"""


def generate_response(
    question: str,
    sql: str,
    rows: list[dict],
    row_count: int,
    truncated: bool,
) -> dict:
    if not rows:
        return {
            "success": True,
            "answer": (
                "No results were found for your question. "
                "This could mean there is no data matching your criteria "
                "in the selected time period, or the category/item you asked about "
                "may not exist in the database."
            ),
            "error": "",
        }

    rows_for_prompt = rows[:MAX_RESPONSE_ROWS]
    results_text = _format_rows_for_prompt(rows_for_prompt)

    prompt = RESPONSE_GENERATION_PROMPT.format(
        question=question.strip(),
        sql=sql.strip(),
        row_count=row_count,
        max_rows=MAX_RESPONSE_ROWS,
        results_text=results_text,
    )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        answer = response.text.strip()
    except Exception as e:
        answer = _plain_text_fallback(rows_for_prompt, row_count, truncated)
        return {
            "success": True,
            "answer": answer,
            "error": f"Gemini API error (using fallback): {e}",
        }

    if truncated:
        answer += (
            f"\n\n*Note: Only the first {len(rows)} of {row_count} results "
            f"are shown above.*"
        )

    return {
        "success": True,
        "answer": answer,
        "error": "",
    }


def _format_rows_for_prompt(rows: list[dict]) -> str:
    if not rows:
        return "(no rows)"

    if len(rows) == 1:
        row = rows[0]
        lines = [f"  {col}: {_format_value(val)}" for col, val in row.items()]
        return "\n".join(lines)

    lines = []
    for i, row in enumerate(rows, 1):
        parts = [f"{col}={_format_value(val)}" for col, val in row.items()]
        lines.append(f"  {i}. {', '.join(parts)}")
    return "\n".join(lines)


def _format_value(value) -> str:
    if value is None:
        return "NULL"

    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return f"{float(value):.2f}"
    except ImportError:
        pass

    return str(value)


def _plain_text_fallback(rows: list[dict], row_count: int, truncated: bool) -> str:
    lines = [f"Query returned {row_count} result(s):"]
    for i, row in enumerate(rows, 1):
        parts = [f"{col}: {_format_value(val)}" for col, val in row.items()]
        lines.append(f"  {i}. {', '.join(parts)}")
    if truncated:
        lines.append(f"  (showing first {len(rows)} of {row_count} rows)")
    return "\n".join(lines)
