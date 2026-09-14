"""
tests/test_pipeline.py
========================
Pytest test suite for the Text-to-SQL RAG Assistant pipeline.

Covers:
  - SQL extraction logic (unit)
  - SQL validator (unit — no API calls, no DB)
  - ChromaDB retriever (integration — requires ./chroma_db/ to exist)
  - SQL executor (integration — requires MySQL textsql_reader user)
  - Full pipeline (integration — requires Gemini API key + MySQL)

Run all tests:
    pytest tests/ -v

Run only fast unit tests (no API or DB calls):
    pytest tests/ -v -m unit

Run integration tests:
    pytest tests/ -v -m integration
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.sql_generator import _extract_sql
from app.sql_validator import validate_sql
from app.sql_executor import execute_sql
from app.retriever import retrieve_schema, format_schema_for_prompt
from app.sql_generator import generate_sql
from app.responder import generate_response, _format_rows_for_prompt, _format_value
from decimal import Decimal


# =============================================================================
# Markers
# =============================================================================
# Unit tests: pure logic, no external dependencies
# Integration tests: require ChromaDB, MySQL, or Gemini API


# =============================================================================
# Unit Tests — SQL Extraction (_extract_sql)
# =============================================================================

class TestSQLExtraction:
    """Tests for the _extract_sql() helper in sql_generator.py."""

    @pytest.mark.unit
    def test_extract_sql_fenced_sql_tag(self):
        """Strips ```sql ... ``` markdown fences."""
        raw = "```sql\nSELECT * FROM orders\n```"
        assert _extract_sql(raw) == "SELECT * FROM orders"

    @pytest.mark.unit
    def test_extract_sql_fenced_no_tag(self):
        """Strips ``` ... ``` fences with no language tag."""
        raw = "```\nSELECT id FROM users\n```"
        assert _extract_sql(raw) == "SELECT id FROM users"

    @pytest.mark.unit
    def test_extract_sql_plain_select(self):
        """Returns plain SELECT as-is."""
        raw = "SELECT name FROM products LIMIT 5"
        assert _extract_sql(raw) == "SELECT name FROM products LIMIT 5"

    @pytest.mark.unit
    def test_extract_sql_preamble_then_select(self):
        """Extracts SELECT from a response with leading explanation text."""
        raw = "Here is the SQL query:\nSELECT COUNT(*) FROM users"
        assert _extract_sql(raw) == "SELECT COUNT(*) FROM users"

    @pytest.mark.unit
    def test_extract_sql_empty_string(self):
        """Returns empty string for empty input."""
        assert _extract_sql("") == ""

    @pytest.mark.unit
    def test_extract_sql_no_sql_present(self):
        """Returns empty string when no SELECT is found."""
        assert _extract_sql("I cannot answer that question.") == ""

    @pytest.mark.unit
    def test_extract_sql_multiline_query(self):
        """Handles multiline SQL correctly."""
        raw = "```sql\nSELECT p.name, SUM(o.quantity)\nFROM orders o\nJOIN products p ON o.product_id = p.id\nGROUP BY p.id\n```"
        result = _extract_sql(raw)
        assert result.startswith("SELECT")
        assert "SUM(o.quantity)" in result
        assert "GROUP BY" in result

    @pytest.mark.unit
    def test_extract_sql_case_insensitive(self):
        """Handles lowercase sql tag in fences."""
        raw = "```SQL\nselect * from orders\n```"
        result = _extract_sql(raw)
        assert "select" in result.lower()


# =============================================================================
# Unit Tests — SQL Validator
# =============================================================================

class TestSQLValidator:
    """Tests for validate_sql() in sql_validator.py."""

    # ── Legitimate queries — must PASS ────────────────────────────────────

    @pytest.mark.unit
    def test_valid_simple_select(self):
        result = validate_sql("SELECT * FROM orders LIMIT 10")
        assert result["valid"] is True
        assert result["reason"] == ""

    @pytest.mark.unit
    def test_valid_count_query(self):
        result = validate_sql("SELECT COUNT(*) FROM users")
        assert result["valid"] is True

    @pytest.mark.unit
    def test_valid_join_query(self):
        sql = ("SELECT p.name, SUM(o.quantity) AS total "
               "FROM orders o JOIN products p ON o.product_id = p.id "
               "GROUP BY p.id, p.name ORDER BY total DESC LIMIT 5")
        result = validate_sql(sql)
        assert result["valid"] is True

    @pytest.mark.unit
    def test_valid_revenue_query(self):
        sql = "SELECT SUM(amount) FROM payments WHERE status = 'paid'"
        result = validate_sql(sql)
        assert result["valid"] is True

    @pytest.mark.unit
    def test_valid_low_stock_query(self):
        sql = "SELECT name, stock FROM products WHERE stock < 10 ORDER BY stock ASC"
        result = validate_sql(sql)
        assert result["valid"] is True

    @pytest.mark.unit
    def test_valid_having_clause(self):
        sql = ("SELECT u.name, COUNT(o.id) FROM orders o "
               "JOIN users u ON o.user_id = u.id "
               "GROUP BY u.id HAVING COUNT(o.id) > 3")
        result = validate_sql(sql)
        assert result["valid"] is True

    # ── Destructive operations — must FAIL ────────────────────────────────

    @pytest.mark.unit
    def test_blocked_drop(self):
        result = validate_sql("DROP TABLE users")
        assert result["valid"] is False
        assert "DROP" in result["reason"] or "SELECT" in result["reason"]

    @pytest.mark.unit
    def test_blocked_delete(self):
        result = validate_sql("DELETE FROM orders")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_insert(self):
        result = validate_sql("INSERT INTO users VALUES (1,'x','y','z',NOW())")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_update(self):
        result = validate_sql("UPDATE products SET price = 0")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_alter(self):
        result = validate_sql("ALTER TABLE orders ADD COLUMN x INT")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_truncate(self):
        result = validate_sql("TRUNCATE TABLE orders")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_create(self):
        result = validate_sql("CREATE TABLE hacked (id INT)")
        assert result["valid"] is False

    # ── Injection patterns — must FAIL ────────────────────────────────────

    @pytest.mark.unit
    def test_blocked_union(self):
        result = validate_sql("SELECT * FROM users UNION SELECT * FROM payments")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_stacked_statements(self):
        result = validate_sql("SELECT * FROM users; DROP TABLE users")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_comment_injection(self):
        result = validate_sql("SELECT * FROM users -- ignore everything")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_load_file(self):
        result = validate_sql("SELECT LOAD_FILE('/etc/passwd')")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_information_schema(self):
        result = validate_sql("SELECT * FROM information_schema.tables")
        assert result["valid"] is False

    # ── Edge cases ────────────────────────────────────────────────────────

    @pytest.mark.unit
    def test_blocked_empty_string(self):
        result = validate_sql("")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_too_short(self):
        result = validate_sql("SELECT")
        assert result["valid"] is False

    @pytest.mark.unit
    def test_blocked_whitespace_only(self):
        result = validate_sql("   ")
        assert result["valid"] is False


# =============================================================================
# Unit Tests — Responder helpers
# =============================================================================

class TestResponderHelpers:
    """Tests for helper functions in responder.py."""

    @pytest.mark.unit
    def test_format_value_decimal(self):
        """Decimal values are formatted to 2 decimal places."""
        assert _format_value(Decimal("4477662.23")) == "4477662.23"

    @pytest.mark.unit
    def test_format_value_none(self):
        """None is formatted as NULL."""
        assert _format_value(None) == "NULL"

    @pytest.mark.unit
    def test_format_value_int(self):
        assert _format_value(42) == "42"

    @pytest.mark.unit
    def test_format_value_string(self):
        assert _format_value("Bengaluru") == "Bengaluru"

    @pytest.mark.unit
    def test_format_rows_single_row(self):
        """Single row uses key: value format."""
        rows = [{"total": 2000}]
        result = _format_rows_for_prompt(rows)
        assert "total: 2000" in result

    @pytest.mark.unit
    def test_format_rows_multi_row(self):
        """Multiple rows use numbered list format."""
        rows = [{"name": "A", "stock": 5}, {"name": "B", "stock": 3}]
        result = _format_rows_for_prompt(rows)
        assert "1." in result
        assert "2." in result

    @pytest.mark.unit
    def test_format_rows_empty(self):
        assert _format_rows_for_prompt([]) == "(no rows)"


# =============================================================================
# Integration Tests — Retriever
# =============================================================================

class TestRetriever:
    """Integration tests for retrieve_schema() and format_schema_for_prompt()."""

    @pytest.mark.integration
    def test_retrieve_orders_and_products_for_sales_question(self):
        """Sales volume questions should retrieve orders and products."""
        results = retrieve_schema("Which product sold the most this month?")
        tables = [r["table_name"] for r in results]
        assert "orders" in tables
        assert "products" in tables

    @pytest.mark.integration
    def test_retrieve_users_for_signup_question(self):
        """User sign-up questions should retrieve users table."""
        results = retrieve_schema("How many users signed up last week?")
        tables = [r["table_name"] for r in results]
        assert "users" in tables

    @pytest.mark.integration
    def test_retrieve_payments_for_revenue_question(self):
        """Revenue questions should retrieve payments table."""
        results = retrieve_schema("What is the total revenue this month?")
        tables = [r["table_name"] for r in results]
        assert "payments" in tables

    @pytest.mark.integration
    def test_retrieve_reviews_for_rating_question(self):
        """Rating/review questions should retrieve reviews table."""
        results = retrieve_schema("Which product has the worst average rating?")
        tables = [r["table_name"] for r in results]
        assert "reviews" in tables

    @pytest.mark.integration
    def test_retrieve_products_for_stock_question(self):
        """Stock questions should retrieve products table."""
        results = retrieve_schema("Which products are running low on stock?")
        tables = [r["table_name"] for r in results]
        assert "products" in tables

    @pytest.mark.integration
    def test_retrieve_returns_top_k_results(self):
        """retrieve_schema returns exactly TOP_K results."""
        from config.settings import TOP_K
        results = retrieve_schema("How many orders were placed yesterday?")
        assert len(results) == TOP_K

    @pytest.mark.integration
    def test_retrieve_similarity_scores_between_0_and_1(self):
        """Similarity scores must be in [0, 1] range."""
        results = retrieve_schema("Show me revenue by category")
        for r in results:
            assert 0.0 <= r["similarity"] <= 1.0

    @pytest.mark.integration
    def test_format_schema_for_prompt_contains_all_tables(self):
        """format_schema_for_prompt includes a section for each retrieved table."""
        results = retrieve_schema("Which product sold the most?")
        formatted = format_schema_for_prompt(results)
        for r in results:
            assert f"--- Schema: {r['table_name']} ---" in formatted


# =============================================================================
# Integration Tests — SQL Executor
# =============================================================================

class TestSQLExecutor:
    """Integration tests for execute_sql() against the MySQL database."""

    @pytest.mark.integration
    def test_execute_count_query(self):
        """Simple COUNT query returns expected row count."""
        result = execute_sql("SELECT COUNT(*) AS total FROM users")
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["rows"][0]["total"] == 2000

    @pytest.mark.integration
    def test_execute_top_products_query(self):
        """JOIN query returns correct columns."""
        sql = ("SELECT p.name, SUM(o.quantity) AS units "
               "FROM orders o JOIN products p ON o.product_id = p.id "
               "GROUP BY p.id ORDER BY units DESC LIMIT 3")
        result = execute_sql(sql)
        assert result["success"] is True
        assert result["columns"] == ["name", "units"]
        assert result["row_count"] == 3

    @pytest.mark.integration
    def test_execute_payments_revenue(self):
        """Revenue query returns a non-zero result."""
        result = execute_sql("SELECT SUM(amount) AS revenue FROM payments WHERE status = 'paid'")
        assert result["success"] is True
        revenue = float(result["rows"][0]["revenue"])
        assert revenue > 0

    @pytest.mark.integration
    def test_execute_returns_dict_rows(self):
        """Rows are returned as dicts, not tuples."""
        result = execute_sql("SELECT id, name FROM products LIMIT 1")
        assert result["success"] is True
        assert isinstance(result["rows"][0], dict)
        assert "id" in result["rows"][0]
        assert "name" in result["rows"][0]

    @pytest.mark.integration
    def test_execute_write_blocked_by_mysql(self):
        """INSERT is rejected at the database level (textsql_reader has no INSERT)."""
        result = execute_sql(
            "INSERT INTO users (name, email, city, created_at) "
            "VALUES ('Hacker', 'h@test.com', 'Delhi', NOW())"
        )
        assert result["success"] is False
        assert "1142" in result["error"]  # MySQL error: command denied

    @pytest.mark.integration
    def test_execute_invalid_sql_returns_error(self):
        """Invalid SQL syntax returns success=False with an error message."""
        result = execute_sql("SELECT FROM WHERE invalid garbage")
        assert result["success"] is False
        assert result["error"] != ""

    @pytest.mark.integration
    def test_execute_truncation_flag(self):
        """truncated=True when row count exceeds MAX_RESULT_ROWS."""
        from config.settings import MAX_RESULT_ROWS
        # orders has 8000 rows — far more than MAX_RESULT_ROWS (100)
        result = execute_sql("SELECT id FROM orders")
        assert result["success"] is True
        assert result["row_count"] > MAX_RESULT_ROWS
        assert result["truncated"] is True
        assert len(result["rows"]) == MAX_RESULT_ROWS


# =============================================================================
# Integration Tests — Full Pipeline
# =============================================================================

class TestFullPipeline:
    """End-to-end integration tests for the complete pipeline."""

    def _run_pipeline(self, question: str) -> dict:
        """Helper: runs all 5 pipeline stages and returns a summary dict."""
        docs = retrieve_schema(question)
        schema_text = format_schema_for_prompt(docs)
        gen = generate_sql(question, schema_text)
        if not gen["success"]:
            return {"success": False, "stage": "sql_generation", "error": gen["error"]}
        val = validate_sql(gen["sql"])
        if not val["valid"]:
            return {"success": False, "stage": "validation", "error": val["reason"]}
        exe = execute_sql(gen["sql"])
        if not exe["success"]:
            return {"success": False, "stage": "execution", "error": exe["error"]}
        resp = generate_response(question, gen["sql"], exe["rows"], exe["row_count"], exe["truncated"])
        return {
            "success": True,
            "sql": gen["sql"],
            "rows": exe["rows"],
            "row_count": exe["row_count"],
            "answer": resp["answer"],
        }

    @pytest.mark.integration
    def test_pipeline_best_selling_product(self):
        result = self._run_pipeline("Which product sold the most this month?")
        assert result["success"] is True
        assert result["sql"].upper().startswith("SELECT")
        assert result["answer"] != ""

    @pytest.mark.integration
    def test_pipeline_user_count(self):
        result = self._run_pipeline("How many users signed up last week?")
        assert result["success"] is True
        assert "users" in result["sql"].lower() or "created_at" in result["sql"].lower()

    @pytest.mark.integration
    def test_pipeline_revenue(self):
        result = self._run_pipeline("What is the total revenue from paid orders?")
        assert result["success"] is True
        assert "paid" in result["sql"].lower()
        assert result["row_count"] >= 1

    @pytest.mark.integration
    def test_pipeline_city_with_most_customers(self):
        result = self._run_pipeline("Which city has the most customers?")
        assert result["success"] is True
        assert result["answer"] != ""

    @pytest.mark.integration
    def test_pipeline_low_stock_products(self):
        result = self._run_pipeline("Show me products that are out of stock")
        assert result["success"] is True
        assert "stock" in result["sql"].lower()

    @pytest.mark.integration
    def test_pipeline_answer_is_natural_language(self):
        """The answer must not contain raw SQL keywords — it should be plain English."""
        result = self._run_pipeline("How many orders were placed this month?")
        assert result["success"] is True
        # Answer should not start with SELECT
        assert not result["answer"].strip().upper().startswith("SELECT")
        # Answer should not expose column names directly in a query-like way
        assert "FROM" not in result["answer"].upper()[:50]
