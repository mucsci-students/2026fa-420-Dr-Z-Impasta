import json
import os
from pathlib import Path

import pytest

from zimpasta.export import ExportFormat, export_schedules, resolve_output_path, unwritable_reason


def test_parse_format_is_case_insensitive():
    assert ExportFormat.parse("csv") is ExportFormat.CSV
    assert ExportFormat.parse("CSV") is ExportFormat.CSV
    assert ExportFormat.parse("Json") is ExportFormat.JSON
    assert ExportFormat.parse(" JSON ") is ExportFormat.JSON
    assert ExportFormat.parse("xml") is None
    assert ExportFormat.parse("") is None


def test_resolve_output_path_appends_extension_when_missing(tmp_path):
    assert (
        resolve_output_path(str(tmp_path / "out"), ExportFormat.CSV)
        == tmp_path.resolve() / "out.csv"
    )
    assert resolve_output_path(str(tmp_path / "out.json"), ExportFormat.JSON) == (
        tmp_path.resolve() / "out.json"
    )
    assert resolve_output_path(str(tmp_path / "OUT.JSON"), ExportFormat.JSON).name == "OUT.JSON"
    assert resolve_output_path(str(tmp_path / "out.csv"), ExportFormat.JSON).name == "out.csv.json"


def test_unwritable_reason(tmp_path):
    assert unwritable_reason(tmp_path / "fresh.csv") is None
    assert unwritable_reason(tmp_path / "missing" / "fresh.csv") is not None
    assert unwritable_reason(tmp_path) is not None
    existing = tmp_path / "existing.csv"
    existing.write_text("x")
    assert unwritable_reason(existing) is None


def test_json_export_writes_one_array_per_schedule(tmp_path, real_schedules):
    path = tmp_path / "out.json"

    result = export_schedules(real_schedules, path, ExportFormat.JSON)

    assert result.path == path
    assert result.schedule_count == 2
    assert result.overwrote is False
    data = json.loads(path.read_bytes().decode("utf-8"))
    assert len(data) == 2
    for schedule, expected in zip(data, real_schedules, strict=True):
        assert [row["course"] for row in schedule] == [i.course_str for i in expected]
        for row in schedule:
            assert {"course", "faculty", "room", "times", "reserve_room_during_lab"} <= row.keys()
            assert all({"day", "start", "duration", "delivery"} <= t.keys() for t in row["times"])


def test_csv_export_matches_library_rows(tmp_path, real_schedules):
    path = tmp_path / "out.csv"

    export_schedules(real_schedules, path, ExportFormat.CSV)

    expected = "\n\n".join("\n".join(i.as_csv() for i in s) for s in real_schedules)
    assert path.read_text(encoding="utf-8") == expected


def test_single_schedule_export(tmp_path, real_schedules):
    path = tmp_path / "one.json"

    result = export_schedules([real_schedules[1]], path, ExportFormat.JSON)

    assert result.schedule_count == 1
    assert len(json.loads(path.read_text(encoding="utf-8"))) == 1


def test_export_refuses_to_overwrite_by_default(tmp_path, real_schedules):
    path = tmp_path / "out.csv"
    path.write_text("keep me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        export_schedules(real_schedules, path, ExportFormat.CSV)

    assert path.read_text(encoding="utf-8") == "keep me"


def test_export_overwrites_when_asked(tmp_path, real_schedules):
    path = tmp_path / "out.csv"
    path.write_text("old", encoding="utf-8")

    result = export_schedules(real_schedules, path, ExportFormat.CSV, overwrite=True)

    assert result.overwrote is True
    assert path.read_text(encoding="utf-8") != "old"


def test_export_rejects_empty_set(tmp_path):
    with pytest.raises(ValueError):
        export_schedules([], tmp_path / "out.csv", ExportFormat.CSV)
    assert not (tmp_path / "out.csv").exists()


def test_export_to_missing_directory_raises_oserror(tmp_path, real_schedules):
    with pytest.raises(OSError):
        export_schedules(real_schedules, tmp_path / "missing" / "out.csv", ExportFormat.CSV)


def test_failed_write_removes_the_claimed_file(tmp_path, real_schedules, monkeypatch):
    path = tmp_path / "out.csv"

    class Broken:
        def __init__(self, filename):
            pass

        def __enter__(self):
            return self

        def add_schedule(self, schedule):
            raise RuntimeError("disk on fire")

        def __exit__(self, *args):
            return None

    monkeypatch.setattr("zimpasta.export.CSVWriter", Broken)

    with pytest.raises(RuntimeError):
        export_schedules(real_schedules, path, ExportFormat.CSV)

    assert not path.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_read_only_file_is_reported_unwritable(tmp_path: Path):
    path = tmp_path / "locked.csv"
    path.write_text("x")
    path.chmod(0o444)
    try:
        if os.access(path, os.W_OK):
            pytest.skip("running with permissions that ignore file modes")
        assert unwritable_reason(path) is not None
    finally:
        path.chmod(0o644)
