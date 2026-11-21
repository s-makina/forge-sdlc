"""Log and artefact collection tests for subphase 3.7."""

from sqlalchemy.orm import Session

from app.schemas.execution import ExecutionCreate
from app.services import events, executions
from app.storage.client import MemoryObjectStore


def _execution(db: Session) -> str:
    execution = executions.create_execution(
        db,
        ExecutionCreate(
            project_id=1,
            repository_url="https://github.com/example/app.git",
            branch="main",
        ),
    )
    return execution.execution_id


def test_record_event_sequences(db_session: Session) -> None:
    execution_id = _execution(db_session)
    first = events.record_event(db_session, execution_id, "start", "begin")
    second = events.record_event(db_session, execution_id, "finish", "end")

    assert first.sequence == 1
    assert second.sequence == 2
    rows = events.list_events(db_session, execution_id)
    assert [r.sequence for r in rows] == [1, 2]


def test_record_command(db_session: Session) -> None:
    execution_id = _execution(db_session)
    event = events.record_command(db_session, execution_id, "pytest", 0)
    assert event.kind == "command"
    assert event.message == "pytest"
    assert event.details == "exit_code=0"


def test_record_tool_call(db_session: Session) -> None:
    execution_id = _execution(db_session)
    event = events.record_tool_call(db_session, execution_id, "edit_file", "ok")
    assert event.kind == "tool_call"
    assert event.message == "edit_file"
    assert event.details == "ok"


def test_list_events_ordered(db_session: Session) -> None:
    execution_id = _execution(db_session)
    events.record_event(db_session, execution_id, "a", "one")
    events.record_event(db_session, execution_id, "b", "two")
    events.record_event(db_session, execution_id, "c", "three")
    rows = events.list_events(db_session, execution_id)
    assert [r.message for r in rows] == ["one", "two", "three"]


def test_store_and_list_artefact(db_session: Session) -> None:
    execution_id = _execution(db_session)
    store = MemoryObjectStore()
    artefact = events.store_artefact(
        db_session,
        store,
        bucket="artifacts",
        execution_id=execution_id,
        name="test-report.xml",
        data=b"<tests/>",
        kind="test_report",
        content_type="application/xml",
    )

    assert artefact.name == "test-report.xml"
    assert artefact.size_bytes == len(b"<tests/>")
    assert artefact.kind == "test_report"
    assert artefact.mime_type == "application/xml"

    stored = store.get("artifacts", f"executions/{execution_id}/test-report.xml")
    assert stored == b"<tests/>"

    listed = events.list_artefacts(db_session, execution_id)
    assert [a.name for a in listed] == ["test-report.xml"]