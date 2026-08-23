import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    connection = psycopg.connect(DATABASE_URL)

    try:
        yield connection
    finally:
        connection.close()