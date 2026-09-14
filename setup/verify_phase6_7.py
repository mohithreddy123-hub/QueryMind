"""
Phase 6 & 7 verification:
  - Tests sql_validator.py (blocklist, allowed queries, edge cases)
  - Tests sql_executor.py (real queries against MySQL using textsql_reader)
"""
import sys 
sys .path .insert (0 ,".")

from app .sql_validator import validate_sql 
from app .sql_executor import execute_sql 

passed =0 
total =0 

def check (label ,condition ,detail =""):
    global passed ,total 
    total +=1 
    ok =bool (condition )
    if ok :passed +=1 
    status ="PASS"if ok else "FAIL"
    print (f"  [{status }] {label }"+(f" | {detail }"if detail else ""))
    return ok 

print ("\n=== CHECK 1: sql_validator — legitimate SELECT queries (must PASS) ===")

legit =[
"SELECT * FROM orders LIMIT 10",
"SELECT COUNT(*) FROM users",
"SELECT p.name, SUM(o.quantity) AS total FROM orders o JOIN products p ON o.product_id = p.id GROUP BY p.id",
"SELECT SUM(amount) FROM payments WHERE status = 'paid'",
"SELECT name, stock FROM products WHERE stock < 10 ORDER BY stock ASC",
"SELECT u.name, COUNT(o.id) FROM orders o JOIN users u ON o.user_id = u.id GROUP BY u.id HAVING COUNT(o.id) > 3",
]
for sql in legit :
    r =validate_sql (sql )
    check (sql [:60 ],r ["valid"],r ["reason"]if not r ["valid"]else "")


print ("\n=== CHECK 2: sql_validator — blocked queries (must FAIL) ===")

blocked =[
("DROP TABLE users","DROP"),
("DELETE FROM orders","DELETE"),
("INSERT INTO users VALUES (1,'a','b','c',NOW())","INSERT"),
("UPDATE products SET price = 0","UPDATE"),
("SELECT * FROM users UNION SELECT * FROM payments","UNION"),
("SELECT * FROM users; DROP TABLE users","stacked"),
("ALTER TABLE orders ADD COLUMN x INT","ALTER"),
("SELECT LOAD_FILE('/etc/passwd')","LOAD_FILE"),
("SELECT * FROM users -- ignore everything","comment injection"),
("SELECT * FROM information_schema.tables","info schema"),
]
for sql ,reason in blocked :
    r =validate_sql (sql )
    check (f"BLOCKED ({reason }): {sql [:50 ]}",not r ["valid"],r ["reason"][:60 ]if r ["reason"]else "WRONGLY PASSED")


print ("\n=== CHECK 3: sql_executor — real queries via textsql_reader ===")

exec_cases =[
{
"label":"Row count: users",
"sql":"SELECT COUNT(*) AS total FROM users",
"expect_columns":["total"],
"expect_rows_gte":1 ,
},
{
"label":"Top product by units sold",
"sql":"SELECT p.name, SUM(o.quantity) AS units FROM orders o JOIN products p ON o.product_id = p.id GROUP BY p.id ORDER BY units DESC LIMIT 3",
"expect_columns":["name","units"],
"expect_rows_gte":1 ,
},
{
"label":"Revenue from paid payments",
"sql":"SELECT SUM(amount) AS revenue FROM payments WHERE status = 'paid'",
"expect_columns":["revenue"],
"expect_rows_gte":1 ,
},
{
"label":"Low stock products",
"sql":"SELECT name, stock FROM products WHERE stock < 10 ORDER BY stock ASC LIMIT 5",
"expect_columns":["name","stock"],
"expect_rows_gte":0 ,
},
]

for tc in exec_cases :
    r =execute_sql (tc ["sql"])
    if not r ["success"]:
        check (tc ["label"],False ,r ["error"])
        continue 
    cols_ok =r ["columns"]==tc ["expect_columns"]
    rows_ok =r ["row_count"]>=tc ["expect_rows_gte"]
    ok =check (
    tc ["label"],
    r ["success"]and cols_ok and rows_ok ,
    f"rows={r ['row_count']}, cols={r ['columns']}, truncated={r ['truncated']}"
    )
    if r ["rows"]:
        print (f"         Sample row: {r ['rows'][0 ]}")


print ("\n=== CHECK 4: sql_executor — read-only enforcement ===")

write_attempt =execute_sql ("INSERT INTO users (name, email, city, created_at) VALUES ('Hacker', 'hack@test.com', 'Delhi', NOW())")
check (
"INSERT blocked by MySQL (textsql_reader has no INSERT privilege)",
not write_attempt ["success"],
write_attempt ["error"][:80 ]if write_attempt ["error"]else "INSERT wrongly succeeded!"
)


print (f"\n{'='*55 }")
print (f"  Result: {passed }/{total } passed")
print (f"  Phase 6 & 7: {'ALL CHECKS PASSED'if passed ==total else 'SOME CHECKS FAILED'}")
print (f"{'='*55 }")
