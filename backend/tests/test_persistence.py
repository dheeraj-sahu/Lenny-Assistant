"""
tests/test_persistence.py

Unit tests for the persistence layer (repositories).
Uses SQLite in-memory to avoid requiring a live PostgreSQL instance.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from persistence.models import Base, Session, Message, Artifact
from persistence.repositories.session_repository import SessionRepository
from persistence.repositories.message_repository import MessageRepository
from persistence.repositories.artifact_repository import ArtifactRepository

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Provide a fresh SQLite DB session for each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_session(db_session):
    repo = SessionRepository(db_session)
    session = await repo.create(active_provider="ollama")
    assert session.id is not None
    assert session.active_provider == "ollama"

    fetched = await repo.get_by_id(session.id)
    assert fetched is not None
    assert fetched.id == session.id


@pytest.mark.asyncio
async def test_session_not_found_returns_none(db_session):
    repo = SessionRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_set_session_title(db_session):
    repo = SessionRepository(db_session)
    session = await repo.create(active_provider="ollama")
    await repo.set_title(session.id, "Test title")
    await db_session.commit()

    fetched = await repo.get_by_id(session.id)
    assert fetched.title == "Test title"


@pytest.mark.asyncio
async def test_list_sessions(db_session):
    repo = SessionRepository(db_session)
    await repo.create(active_provider="ollama")
    await repo.create(active_provider="anthropic")
    await db_session.commit()

    sessions = await repo.list_all()
    assert len(sessions) == 2


@pytest.mark.asyncio
async def test_delete_session(db_session):
    repo = SessionRepository(db_session)
    session = await repo.create(active_provider="ollama")
    await db_session.commit()

    deleted = await repo.delete(session.id)
    assert deleted is True

    result = await repo.get_by_id(session.id)
    assert result is None


@pytest.mark.asyncio
async def test_create_and_list_messages(db_session):
    session_repo = SessionRepository(db_session)
    session = await session_repo.create(active_provider="ollama")
    await db_session.commit()

    msg_repo = MessageRepository(db_session)
    await msg_repo.create(session_id=session.id, role="user", content="Hello")
    await msg_repo.create(session_id=session.id, role="assistant", content="Hi there!")
    await db_session.commit()

    messages = await msg_repo.list_by_session(session.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_create_artifact(db_session):
    session_repo = SessionRepository(db_session)
    session = await session_repo.create(active_provider="ollama")
    await db_session.commit()

    artifact_repo = ArtifactRepository(db_session)
    artifact = await artifact_repo.create(
        session_id=session.id,
        artifact_type="markdown",
        raw_content="# Hello\nWorld",
        sanitized_content="# Hello\nWorld",
        title="Test Artifact",
    )
    await db_session.commit()

    fetched = await artifact_repo.get_by_id(artifact.id)
    assert fetched is not None
    assert fetched.artifact_type == "markdown"
    assert fetched.title == "Test Artifact"


@pytest.mark.asyncio
async def test_list_artifacts_by_session(db_session):
    session_repo = SessionRepository(db_session)
    session = await session_repo.create(active_provider="ollama")
    await db_session.commit()

    artifact_repo = ArtifactRepository(db_session)
    await artifact_repo.create(
        session_id=session.id,
        artifact_type="markdown",
        raw_content="Essay 1",
        sanitized_content="Essay 1",
    )
    await artifact_repo.create(
        session_id=session.id,
        artifact_type="html",
        raw_content="<p>HTML</p>",
        sanitized_content="<p>HTML</p>",
    )
    await db_session.commit()

    artifacts = await artifact_repo.list_by_session(session.id)
    assert len(artifacts) == 2
