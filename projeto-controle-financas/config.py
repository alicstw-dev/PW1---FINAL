import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Se não tiver DATABASE_URL no .env, usa SQLite
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or \
        "sqlite:///" + os.path.join(basedir, "app.db")
