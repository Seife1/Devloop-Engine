import pytest

from learnloop.config import Settings
from learnloop.persistence.db import connect


@pytest.fixture
def settings(tmp_path):
    return Settings(db_path=tmp_path / "test.db")


@pytest.fixture
def conn(settings):
    c = connect(settings.db_path)
    yield c
    c.close()
