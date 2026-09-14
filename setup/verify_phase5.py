"""
Phase 5 verification: tests the full retriever -> sql_generator pipeline.
For each question, retrieves schema from ChromaDB then asks Gemini to generate SQL.
Checks that:
  - generate_sql() returns success=True
  - The returned SQL starts with SELECT
  - No markdown fences remain in the output
  - SQL contains expected keywords for each question
"""
import sys
sys.path.insert(0, ".")

from app.retriever import retrieve_schema, format_schema_for_prompt
from app.sql_generator import generate_sql, _extract_sql

# ── Test 1: _extract_sql() handles all fence formats ──────────────────────
print("=== CHECK 1: SQL extraction edge cases ===")
cases = [
    ("```sql\nSELECT * FROM orders\n```",   "SELECT * FROM orders"),
    ("```\nSELECT id FROM users\n```",        "SELECT id FROM users"),
    ("SELECT name FROM products LIMIT 5",     "SELECT name FROM products LIMIT 5"),
    ("Here is the SQL:\nSELECT COUNT(*) FROM users", "SELECT COUNT(*) FROM users"),
]
extract_ok = True
for raw, expected in cases:
    result = _extract_sql(raw)
    ok = result.strip() == expected.strip()
    if not ok:
        extract_ok = False
    print(f"  [{'PASS' if ok else 'FAIL'}] Input: {raw[:40]!r}")
    if not ok:
        print(f"         Expected: {expected!r}")
        print(f"         Got:      {result!r}")

# ── Test 2: End-to-end retrieval -> generation ─────────────────────────────
print("\n=== CHECK 2: End-to-end retrieve -> generate_sql ===")

test_questions = [
    {
        "question": "Which product sold the most this month?",
        "must_contain_keywords": ["SELECT", "orders", "products", "quantity"],
    },
    {
        "question": "How many users signed up last week?",
        "must_contain_keywords": ["SELECT", "users", "created_at"],
    },
    {
        "question": "What is the total revenue this month?",
        "must_contain_keywords": ["SELECT", "payments", "amount", "paid"],
    },
    {
        "question": "Which products are running low on stock?",
        "must_contain_keywords": ["SELECT", "products", "stock"],
    },
]

all_passed = True
for tc in test_questions:
    q = tc["question"]
    print(f"\n  Q: {q}")

    # Retrieve schema
    docs = retrieve_schema(q)
    schema_text = format_schema_for_prompt(docs)
    retrieved_tables = [d["table_name"] for d in docs]
    print(f"     Retrieved tables: {retrieved_tables}")

    # Generate SQL
    result = generate_sql(q, schema_text)

    if not result["success"]:
        print(f"     [FAIL] generate_sql failed: {result['error']}")
        all_passed = False
        continue

    sql = result["sql"]
    print(f"     Generated SQL:\n       {sql[:200].replace(chr(10), chr(10)+'       ')}")

    # Checks
    starts_with_select = sql.strip().upper().startswith("SELECT")
    no_fences = "```" not in sql
    keywords_present = all(
        kw.lower() in sql.lower() for kw in tc["must_contain_keywords"]
    )
    missing = [kw for kw in tc["must_contain_keywords"] if kw.lower() not in sql.lower()]

    ok = starts_with_select and no_fences and keywords_present
    if not ok:
        all_passed = False

    print(f"     Starts with SELECT : {'PASS' if starts_with_select else 'FAIL'}")
    print(f"     No markdown fences : {'PASS' if no_fences else 'FAIL'}")
    print(f"     Keywords present   : {'PASS' if keywords_present else 'FAIL'}" +
          (f" (missing: {missing})" if missing else ""))
    print(f"     Overall            : {'PASS' if ok else 'FAIL'}")

print("\n" + "=" * 60)
phase5_ok = extract_ok and all_passed
print(f"Phase 5: {'ALL CHECKS PASSED' if phase5_ok else 'SOME CHECKS FAILED'}")
print("=" * 60)
