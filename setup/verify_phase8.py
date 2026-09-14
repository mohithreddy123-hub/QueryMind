"""
Phase 8 verification: runs the complete pipeline end-to-end.
Question -> Retriever -> SQL Generator -> Validator -> Executor -> Responder
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from app.retriever import retrieve_schema, format_schema_for_prompt
from app.sql_generator import generate_sql
from app.sql_validator import validate_sql
from app.sql_executor import execute_sql
from app.responder import generate_response

QUESTIONS = [
    "Which product sold the most this month?",
    "What is the total revenue from paid orders?",
    "Which city has the most customers?",
]

passed = 0
for q in QUESTIONS:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print(f"{'='*60}")

    # 1. Retrieve
    docs = retrieve_schema(q)
    schema_text = format_schema_for_prompt(docs)
    print(f"  [1] Retrieved: {[d['table_name'] for d in docs]}")

    # 2. Generate SQL
    gen = generate_sql(q, schema_text)
    if not gen["success"]:
        print(f"  [2] FAIL — SQL generation: {gen['error']}")
        continue
    print(f"  [2] SQL: {gen['sql'][:100]}")

    # 3. Validate
    val = validate_sql(gen["sql"])
    if not val["valid"]:
        print(f"  [3] FAIL — Validation: {val['reason']}")
        continue
    print(f"  [3] Validation: PASS")

    # 4. Execute
    exe = execute_sql(gen["sql"])
    if not exe["success"]:
        print(f"  [4] FAIL — Execution: {exe['error']}")
        continue
    print(f"  [4] Executed: {exe['row_count']} rows")

    # 5. Respond
    resp = generate_response(q, gen["sql"], exe["rows"], exe["row_count"], exe["truncated"])
    if not resp["success"]:
        print(f"  [5] FAIL — Responder: {resp['error']}")
        continue

    print(f"\n  Answer:")
    print(f"  {resp['answer']}")
    passed += 1

print(f"\n{'='*60}")
print(f"Phase 8: {passed}/{len(QUESTIONS)} end-to-end tests PASSED")
print(f"{'='*60}")
