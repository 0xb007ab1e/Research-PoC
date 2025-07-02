import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from repository import TenantAwareDB
from models import ContextCreateRequest
from main import app

test_database_url = "postgresql://user:password@localhost:5432/test_db"

engine = create_engine(test_database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = TenantAwareDB()
client = TestClient(app)

@pytest.fixture(scope="module")
def test_app():
    # Override the application dependencies for testing
    app.dependency_overrides[TenantAwareDB] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def context_create_request():
    return ContextCreateRequest(
        context_data={"key": "value"},
        context_type="test_type"
    )

