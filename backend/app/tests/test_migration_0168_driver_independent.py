from pathlib import Path


def test_0168_does_not_depend_on_driver_inserted_primary_key() -> None:
    migration = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "0168_remove_profile_dashboard_queries.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert "result.inserted_primary_key" not in source
    assert "dashboards.c.code == dashboard_code" in source
    assert ".scalar_one()" in source


def test_0168_reuses_dashboard_created_by_an_interrupted_attempt() -> None:
    migration = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "0168_remove_profile_dashboard_queries.py"
    )
    source = migration.read_text(encoding="utf-8")

    lookup_position = source.index("dashboard_id = bind.execute(")
    insert_position = source.index("bind.execute(dashboards.insert()")
    assert lookup_position < insert_position
    assert "if dashboard_id is None:" in source
