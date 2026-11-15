
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env from the same folder as config.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE, override=True)

database_url = os.getenv("DATABASE_URL", "sqlite:///shop_faq_bot.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY", "dev-only-change-this-secret"
    )

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    PERMANENT_SESSION_LIFETIME = timedelta(days=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL = os.getenv(
        "RESEND_FROM_EMAIL",
        "Shop FAQ Bot <onboarding@resend.dev>"
    )
    RESEND_TEST_MODE = (
        os.getenv("RESEND_TEST_MODE", "true").lower() == "true"
    )
