"""
Phase 2 verification script.
Checks:
  1. Row counts match configured volumes
  2. A multi-table JOIN works (FK integrity)
  3. Read-only user (textsql_reader) can SELECT
  4. Read-only user cannot INSERT (must raise an error)
"""
import mysql.connector
import sys
sys.path.insert(0, ".")
from config.settings import (
    MYSQL_ADMIN_HOST, MYSQL_ADMIN_PORT, MYSQL_ADMIN_USER, MYSQL_ADMIN_PASSWORD,
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD,
    MYSQL_DATABASE,
    NUM_USERS, NUM_PRODUCTS, NUM_ORDERS, NUM_PAYMENTS, NUM_REVIEWS,
)

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((status, label, detail))
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {label}" + (f" | {detail}" if detail else ""))

# ── Admin connection ──────────────────────────────────────────────────────
admin = mysql.connector.connect(
    host=MYSQL_ADMIN_HOST, port=MYSQL_ADMIN_PORT,
    user=MYSQL_ADMIN_USER, password=MYSQL_ADMIN_PASSWORD,
    database=MYSQL_DATABASE,
)
cur = admin.cursor()

print("\n=== CHECK 1: Row counts ===")
expected = {
    "users": NUM_USERS, "products": NUM_PRODUCTS,
    "orders": NUM_ORDERS, "payments": NUM_PAYMENTS, "reviews": NUM_REVIEWS,
}
for table, exp in expected.items():
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    actual = cur.fetchone()[0]
    check(f"{table}: {actual:,} rows", actual == exp, f"expected {exp:,}")

print("\n=== CHECK 2: JOIN query (FK integrity) ===")
cur.execute("""
    SELECT p.name, SUM(o.quantity) AS total_sold
    FROM orders o
    JOIN products p ON o.product_id = p.id
    GROUP BY p.id, p.name
    ORDER BY total_sold DESC
    LIMIT 5
""")
rows = cur.fetchall()
check("Top-5 products JOIN query", len(rows) == 5, f"returned {len(rows)} rows")
print("    Top 5 products by units sold:")
for name, qty in rows:
    print(f"      {name[:45]:<45} {qty:>5} units")

print("\n=== CHECK 3: Read-only user — SELECT ===")
try:
    ro = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )
    ro_cur = ro.cursor()
    ro_cur.execute("SELECT COUNT(*) FROM users")
    count = ro_cur.fetchone()[0]
    check("textsql_reader can SELECT", count == NUM_USERS, f"got {count:,} users")
    ro_cur.close()
except mysql.connector.Error as e:
    check("textsql_reader can SELECT", False, str(e))

print("\n=== CHECK 4: Read-only user — INSERT must be rejected ===")
try:
    ro_cur2 = ro.cursor()
    ro_cur2.execute("INSERT INTO users (name, email, city, created_at) VALUES ('Hacker', 'hack@test.com', 'Mumbai', NOW())")
    ro.commit()
    check("textsql_reader INSERT rejected at DB level", False, "INSERT succeeded — user has write access!")
    ro_cur2.close()
except mysql.connector.Error as e:
    check("textsql_reader INSERT rejected at DB level", True, f"correctly blocked: {e.errno}")
finally:
    try:
        ro.close()
    except Exception:
        pass

cur.close()
admin.close()

print("\n" + "=" * 50)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
print(f"  Result: {passed} passed, {failed} failed")
if failed == 0:
    print("  Phase 2: ALL CHECKS PASSED")
else:
    print("  Phase 2: SOME CHECKS FAILED")
print("=" * 50)
