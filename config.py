import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "conditional_engine")
DB_TEST_NAME = os.getenv("DB_TEST_NAME", "conditional_engine_test")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
