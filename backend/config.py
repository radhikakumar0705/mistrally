import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_jwt_key")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+mysqlconnector://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}"
        f"@{os.getenv('DB_HOST', 'localhost')}/{os.getenv('DB_NAME', 'mistrally')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
