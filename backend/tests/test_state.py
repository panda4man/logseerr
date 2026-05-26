import pytest
from app import state as state_module


@pytest.fixture(autouse=True)
def use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(state_module, "DB_PATH", tmp_path / "state.db")


async def test_get_returns_none_when_missing():
    result = await state_module.get_last_ingested("plex")
    assert result is None


async def test_set_and_get():
    await state_module.set_last_ingested("plex", 1716768000000000000)
    result = await state_module.get_last_ingested("plex")
    assert result == 1716768000000000000


async def test_set_updates_existing():
    await state_module.set_last_ingested("plex", 1000)
    await state_module.set_last_ingested("plex", 2000)
    assert await state_module.get_last_ingested("plex") == 2000


async def test_separate_services_are_independent():
    await state_module.set_last_ingested("plex", 1000)
    await state_module.set_last_ingested("sonarr", 2000)
    assert await state_module.get_last_ingested("plex") == 1000
    assert await state_module.get_last_ingested("sonarr") == 2000
