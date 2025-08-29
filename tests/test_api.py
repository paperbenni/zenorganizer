from fastapi.testclient import TestClient
from zeno.api import app

client = TestClient(app)


def test_get_memories(mocker):
    # Mock the storage.get_memories function
    mocker.patch("zeno.storage.get_memories", return_value="Test memories")

    response = client.get("/memories")
    assert response.status_code == 200
    assert response.text == "Test memories"


def test_agent_endpoints(mocker):
    # Mock the agent builder functions
    mock_builder = mocker.patch("zeno.api.build_deduplicator_agent")
    mocker.patch("zeno.api.build_aggregator_agent")
    mocker.patch("zeno.api.build_splitter_agent")
    mocker.patch("zeno.api.build_garbage_collector_agent")
    mocker.patch("zeno.api.build_reminder_agent")

    endpoints = [
        "/deduplicate",
        "/aggregate",
        "/split",
        "/garbage_collect",
        "/reminders",
    ]

    for endpoint in endpoints:
        response = client.post(endpoint)
        assert response.status_code == 202
        assert "task_id" in response.json()


def test_get_task_status(mocker):
    # Mock the _tasks and _results dictionaries
    mocker.patch.dict("zeno.api._tasks", {"test_task": "dummy_task"})
    mocker.patch.dict("zeno.api._results", {"test_task": {"status": "done"}})

    response = client.get("/tasks/test_task")
    assert response.status_code == 200
    assert response.json() == {"status": "done"}

    response = client.get("/tasks/unknown_task")
    assert response.status_code == 404


def test_get_old_messages(mocker):
    # Mock the storage.get_old_messages function
    mocker.patch("zeno.storage.get_old_messages", return_value=[])

    response = client.get("/old_messages")
    assert response.status_code == 200
