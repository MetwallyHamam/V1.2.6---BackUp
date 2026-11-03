from pathlib import Path


def test_0074_buffers_and_closes_select_before_per_row_updates() -> None:
    migration = Path(__file__).parents[2] / "alembic" / "versions" / "0074_product_scoped_sla.py"
    source = migration.read_text(encoding="utf-8")
    select_position = source.index("result = bind.execute")
    buffer_position = source.index("rows = list(result.mappings().all())")
    close_position = source.index("result.close()")
    update_position = source.index("for row in rows:")
    assert select_position < buffer_position < close_position < update_position


def test_0074_uses_driver_independent_sql_server_constraint_drop() -> None:
    migration = Path(__file__).parents[2] / "alembic" / "versions" / "0074_product_scoped_sla.py"
    source = migration.read_text(encoding="utf-8")
    assert "get_unique_constraints" not in source
    assert "sys.key_constraints" in source
    assert "ALTER TABLE sla_targets DROP CONSTRAINT uq_sla_target_service_priority" in source


def test_0074_supplies_existing_type_for_sql_server_nullability_change() -> None:
    migration = Path(__file__).parents[2] / "alembic" / "versions" / "0074_product_scoped_sla.py"
    source = migration.read_text(encoding="utf-8")
    compact = " ".join(source.split())
    assert '"sla_targets", "context_key", existing_type=sa.String(120), nullable=False' in compact
