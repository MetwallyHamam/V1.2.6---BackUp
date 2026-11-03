from pathlib import Path


def _source() -> str:
    migration = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "0169_dashboard_template_destinations.py"
    )
    return migration.read_text(encoding="utf-8")


def test_0169_buffers_widget_rows_before_inserting_clones() -> None:
    source = _source()

    select_position = source.index("source_widgets = bind.execute(")
    buffer_position = source.index(").mappings().all()", select_position)
    insert_position = source.index("widgets.insert().values(", buffer_position)
    assert select_position < buffer_position < insert_position


def test_0169_moves_top_management_assignments_to_destination_clone() -> None:
    source = _source()

    assert 'destination="TOP_MANAGEMENT"' in source
    assert 'assignments.c.dashboard_type == "TOP_MANAGEMENT"' in source
    assert ".values(dashboard_id=clone_id)" in source
