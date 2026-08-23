import psycopg


DATABASE_URL = "dbname=school_management user=aviralsharma"


def get_db():
    connection = psycopg.connect(DATABASE_URL)

    try:
        yield connection
    finally:
        connection.close()