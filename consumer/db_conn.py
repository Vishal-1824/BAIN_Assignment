import os
import urllib.parse

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

def get_db_url():
    db_url = ""
    try:
        db_user = os.getenv("POSTGRES_USER", default=None)
        db_password = urllib.parse.quote_plus(
            os.getenv("POSTGRES_PASSWORD", default=None)
        )
        db_host = "postgres_db"
        db_port ="5432"
        db_name = os.getenv("POSTGRES_DB", default=None)
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        return db_url
    except EnvironmentError as e:
        print(f"An error occurred while getting the database URL: {str(e)}")
    except Exception as e:
        print(f"An error occurred while getting the database URL: {str(e)}")



# Create the database engine
DATABASE_URL = get_db_url()
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

Session = sessionmaker(bind=engine)
metadata = MetaData()

# Create all tables in the database
# This will create tables if they don't exist
# def create_db_and_tables():
#     Base.metadata.create_all(bind=engine)
