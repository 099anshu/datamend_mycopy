import importlib

import pytest


@pytest.fixture
def audit_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAMEND_AUDIT_DIR", str(tmp_path))
    from audit import audit_log
    importlib.reload(audit_log)
    return audit_log


def test_record_and_retrieve_event(audit_module):
    event = audit_module.record_event(
        dataset_id="abc123", actor="user", action="rule_validation_run",
        details={"totalViolations": 4},
    )
    trail = audit_module.get_audit_trail("abc123")
    assert len(trail) == 1
    assert trail[0].eventId == event.eventId
    assert trail[0].action == "rule_validation_run"


def test_filters_by_dataset_id(audit_module):
    audit_module.record_event(dataset_id="a", actor="user", action="upload")
    audit_module.record_event(dataset_id="b", actor="model", action="repair_applied")
    assert len(audit_module.get_audit_trail("a")) == 1
    assert len(audit_module.get_audit_trail("b")) == 1
    assert len(audit_module.get_audit_trail()) == 2


def test_empty_when_no_log_file(audit_module):
    assert audit_module.get_audit_trail("nonexistent") == []
