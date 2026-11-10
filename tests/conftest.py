# tests/conftest.py

import os
import sys
import subprocess
import time
import logging
from typing import Generator, Dict, List
from contextlib import contextmanager

import pytest
import requests
from faker import Faker
from playwright.sync_api import sync_playwright, Browser, Page
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.database import Base, get_engine, get_sessionmaker
from app.models.user import User

# ======================================================================================
# Logging Configuration
# ======================================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================================================================================
# Database Configuration
# ======================================================================================
fake = Faker()
Faker.seed(12345)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")

# Use only the isolated test URL, never the application database.
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import make_url

test_url = make_url(TEST_DATABASE_URL)
if test_url.get_backend_name() != "sqlite" and not (test_url.database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must name a disposable database ending in _test")

test_engine = create_engine(TEST_DATABASE_URL, **(
    {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    if test_url.get_backend_name() == "sqlite" else {}
))
TestingSessionLocal = get_sessionmaker(engine=test_engine)

# ======================================================================================
# Helper Functions
# ======================================================================================
def create_fake_user() -> Dict[str, str]:
    """
    Generate a dictionary of fake user data for testing.

    Returns:
        A dict containing user fields with fake data.
    """
    return {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),  # Ensure uniqueness where necessary
        "username": fake.unique.user_name(),
        "password": "TestPass123!"
    }

@contextmanager
def managed_db_session():
    """
    Context manager for safe database session handling.
    Automatically handles rollback and cleanup.

    Example:
        with managed_db_session() as session:
            user = session.query(User).first()
    """
    session = TestingSessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

# ======================================================================================
# Server Startup / Healthcheck
# ======================================================================================
def wait_for_server(url: str, timeout: int = 30) -> bool:
    """
    Wait for server to be ready, raising an error if it never becomes available.
    """
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    return False

class ServerStartupError(Exception):
    """Raised when the test server fails to start properly"""
    pass

# ======================================================================================
# Primary Database Fixtures
# ======================================================================================
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Tests create tables only on the explicitly isolated test engine.
    Base.metadata.create_all(bind=test_engine)
    yield
    test_engine.dispose()


@pytest.fixture
def db_session():
    with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            session.rollback()
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()


# ======================================================================================
# Test Data Fixtures
# ======================================================================================
@pytest.fixture
def fake_user_data() -> Dict[str, str]:
    """Provide a dictionary of fake user data."""
    return create_fake_user()

@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Create and return a single test user.
    """
    user_data = create_fake_user()
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    logger.info(f"Created test user with ID: {user.id}")
    return user

@pytest.fixture
def seed_users(db_session: Session, request) -> List[User]:
    """
    Create multiple test users in the database.

    Usage:
        @pytest.mark.parametrize("seed_users", [10], indirect=True)
        def test_many_users(seed_users):
            # test logic
    """
    try:
        num_users = request.param
    except AttributeError:
        num_users = 5

    users = []
    for _ in range(num_users):
        user_data = create_fake_user()
        user = User(**user_data)
        users.append(user)
        db_session.add(user)

    db_session.commit()
    logger.info(f"Seeded {len(users)} users into the test database.")
    return users

# ======================================================================================
# FastAPI Server Fixture (Optional)
# ======================================================================================
@pytest.fixture(scope="session")
def fastapi_server():
    """
    Start and manage a FastAPI test server, if needed for integration tests.
    """
    server_url = 'http://127.0.0.1:8000/'
    logger.info("Starting test server...")

    try:
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(server_url, timeout=30):
            raise ServerStartupError("Failed to start test server")

        logger.info("Test server started successfully.")
        yield  # Run all tests that depend on this fixture

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
    finally:
        logger.info("Terminating test server...")
        process.terminate()
        try:
            process.wait(timeout=5)
            logger.info("Test server terminated gracefully.")
        except subprocess.TimeoutExpired:
            logger.warning("Test server did not terminate in time; killing it.")
            process.kill()

# ======================================================================================
# Browser and Page Fixtures (Optional)
# ======================================================================================
@pytest.fixture(scope="session")
def browser_context():
    """
    Provide a Playwright browser context for UI tests.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        logger.info("Playwright browser launched.")
        try:
            yield browser
        finally:
            logger.info("Closing Playwright browser.")
            browser.close()

@pytest.fixture
def page(browser_context: Browser):
    """
    Provide a new browser page for each test.
    """
    context = browser_context.new_context(
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True
    )
    page = context.new_page()
    logger.info("Created new browser page.")
    try:
        yield page
    finally:
        logger.info("Closing browser page and context.")
        page.close()
        context.close()

# ======================================================================================
# Pytest Command-Line Options and Test Collection
# ======================================================================================
def pytest_addoption(parser):
    """
    Add command line options like --preserve-db or --run-slow, if needed.
    """
    parser.addoption(
        "--preserve-db",
        action="store_true",
        default=False,
        help="Keep test database after tests, and skip table truncation."
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow"
    )

def pytest_collection_modifyitems(config, items):
    """
    Automatically skip slow tests unless --run-slow is specified.
    """
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="use --run-slow to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

# ======================================================================================
# How to Use This File
# ======================================================================================
"""
Basic Examples:

1. Test DB operations:
   def test_create_user(db_session):
       user = User(username="test", email="test@example.com")
       db_session.add(user)
       db_session.commit()

2. Using fake data:
   def test_with_fake_data(fake_user_data):
       user = User(**fake_user_data)
       # proceed with test logic...

3. Working with a test user:
   def test_user_update(test_user):
       test_user.username = "new_username"
       # test logic...

4. Testing with multiple users:
   @pytest.mark.parametrize('seed_users', [10], indirect=True)
   def test_user_list(seed_users):
       # seed_users contains 10 test users
       assert len(seed_users) == 10

Command Examples:
- Basic run: pytest
- Keep database afterward (skip table truncation & drop): pytest --preserve-db
- Include slow tests: pytest --run-slow
- Show output: pytest -v -s
"""
