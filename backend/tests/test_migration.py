import ast
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from alembic.config import Config


class TestAlembicMigration:
    """Integration test for Alembic migration validity."""

    @pytest.fixture
    def backend_dir(self):
        return Path(__file__).parent.parent

    @pytest.fixture
    def migration_file(self, backend_dir):
        return backend_dir / "alembic" / "versions" / "f3c8a2b91c4e_add_profesional_id_and_auth_columns.py"

    def test_migration_file_is_valid_python(self, migration_file):
        """Scenario: El script de migración es Python válido."""
        assert migration_file.exists(), f"Migration file not found: {migration_file}"
        source = migration_file.read_text()
        tree = ast.parse(source)
        assert tree is not None

    def test_migration_has_upgrade_and_downgrade(self, migration_file):
        """Scenario: La migración define upgrade y downgrade."""
        source = migration_file.read_text()
        tree = ast.parse(source)
        funcs = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        assert "upgrade" in funcs
        assert "downgrade" in funcs

    def test_migration_revision_chain(self, backend_dir):
        """Scenario: La migración está correctamente encadenada."""
        alembic_ini = backend_dir / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini not found"
        alembic_cfg = Config(str(alembic_ini))
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()
        # The migration tree must converge to a single head (no branches left
        # over from removed/downgraded revisions).
        assert len(heads) == 1, f"Expected exactly 1 head, got {heads}"

    def test_migration_contains_expected_operations(self, migration_file):
        """Scenario: La migración contiene las operaciones esperadas."""
        source = migration_file.read_text()

        # Check for expected schema changes in upgrade
        assert "profesional_id" in source
        assert "email" in source
        assert "password_hash" in source
        assert "api_key" in source
        assert "is_active" in source
        assert "google_refresh_token" in source
        assert "telegram_bot_token" in source
        assert "telegram_secret_token" in source
        assert "uq_paciente_profesional_dni" in source
        assert "ix_lista_de_espera_profesional_paciente" in source
        assert "fk_paciente_profesional" in source
        assert "fk_lista_de_espera_profesional" in source
