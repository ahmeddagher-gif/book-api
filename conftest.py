import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from db_connection import get_db
from db_models import base
import test_my_funcs  # Import the test version
import my_funcs  # Import the original

# Override the functions that use Redis
my_funcs.get_book = test_my_funcs.get_book
my_funcs.update_book = test_my_funcs.update_book
my_funcs.delete_book = test_my_funcs.delete_book

# The rest is the same
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def setup_database():
    base.metadata.create_all(bind=engine)
    yield
    base.metadata.drop_all(bind=engine)
    #import os
    #if os.path.exists("test.db"):
     #   try:
      #      os.remove("test.db")
       # except PermissionError:
        #    print("Warning: Could not delete test.db - file is in use")