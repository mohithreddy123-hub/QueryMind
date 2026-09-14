import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

GEMINI_MODEL: str = "gemini-3.5-flash-lite"

EMBEDDING_MODEL: str = "gemini-embedding-001"

CHROMA_PERSIST_DIR: str = "./chroma_db"

CHROMA_COLLECTION_NAME: str = "schema_docs"

TOP_K: int = 3

MYSQL_HOST: str = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER: str = os.environ.get("MYSQL_USER", "textsql_reader")
MYSQL_PASSWORD: str = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE: str = os.environ.get("MYSQL_DATABASE", "text_to_sql_db")

MYSQL_ADMIN_HOST: str = os.environ.get("MYSQL_ADMIN_HOST", "localhost")
MYSQL_ADMIN_PORT: int = int(os.environ.get("MYSQL_ADMIN_PORT", "3306"))
MYSQL_ADMIN_USER: str = os.environ.get("MYSQL_ADMIN_USER", "root")
MYSQL_ADMIN_PASSWORD: str = os.environ.get("MYSQL_ADMIN_PASSWORD", "")

NUM_USERS: int = 2000
NUM_PRODUCTS: int = 300
NUM_ORDERS: int = 8000
NUM_PAYMENTS: int = 8000
NUM_REVIEWS: int = 5000

MAX_RESULT_ROWS: int = 100
