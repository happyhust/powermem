"""Tests for the seekdb default vector store registration and zero-config wiring.

seekdb is OceanBase's embedded mode — same backend class, same SQL surface,
only configuration differs. These tests pin that contract:

  - the ``seekdb`` provider routes to ``OceanBaseVectorStore``
  - ``SeekDBConfig()`` boots in embedded mode (no host, on-disk ``ob_path``)
  - ``MemoryConfig()`` with no env vars picks ``seekdb`` as the default
  - ``DatabaseSettings`` reads ``seekdb`` as its default provider
  - **Namespace isolation**: SEEKDB_* and OCEANBASE_* envs are NOT shared
    (each provider reads only its own namespace)
  - OceanBase requires a non-empty host and rejects OCEANBASE_PATH
"""

from __future__ import annotations

import pytest


def test_seekdb_vector_provider_is_registered():
    from powermem.storage.config.base import BaseVectorStoreConfig

    # Importing storage.factory triggers registry population for all providers.
    import powermem.storage.factory  # noqa: F401

    assert BaseVectorStoreConfig.has_provider("seekdb")
    assert (
        BaseVectorStoreConfig.get_provider_class_path("seekdb")
        == "powermem.storage.oceanbase.oceanbase.OceanBaseVectorStore"
    )


def test_seekdb_shares_backend_class_with_oceanbase():
    """The whole point of this provider: same code, different config."""
    from powermem.storage.config.base import BaseVectorStoreConfig

    import powermem.storage.factory  # noqa: F401

    seekdb_path = BaseVectorStoreConfig.get_provider_class_path("seekdb")
    oceanbase_path = BaseVectorStoreConfig.get_provider_class_path("oceanbase")
    assert seekdb_path == oceanbase_path


def test_seekdb_graph_provider_is_registered():
    from powermem.storage.config.base import BaseGraphStoreConfig

    import powermem.storage.factory  # noqa: F401

    assert BaseGraphStoreConfig.has_provider("seekdb")
    assert (
        BaseGraphStoreConfig.get_provider_class_path("seekdb")
        == "powermem.storage.oceanbase.oceanbase_graph.MemoryGraph"
    )


def test_seekdb_config_defaults_to_embedded_mode():
    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()

    # Empty host triggers embedded seekdb inside OceanBaseVectorStore.
    assert cfg.host == ""
    assert cfg.ob_path == "./seekdb_data"
    assert cfg._provider_name == "seekdb"
    assert cfg.to_component_dict()["provider"] == "seekdb"


def test_seekdb_config_reads_SEEKDB_env_aliases(monkeypatch):
    monkeypatch.setenv("SEEKDB_PATH", "./custom_seekdb")
    monkeypatch.setenv("SEEKDB_DATABASE", "my_powermem")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.ob_path == "./custom_seekdb"
    assert cfg.db_name == "my_powermem"


def test_seekdb_config_reads_SEEKDB_schema_shape_aliases(monkeypatch):
    monkeypatch.setenv("SEEKDB_TEXT_FIELD", "doc")
    monkeypatch.setenv("SEEKDB_VECTOR_FIELD", "vec")
    monkeypatch.setenv("SEEKDB_PRIMARY_FIELD", "row_id")
    monkeypatch.setenv("SEEKDB_METADATA_FIELD", "meta")
    monkeypatch.setenv("SEEKDB_VIDX_NAME", "custom_vidx")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.text_field == "doc"
    assert cfg.vector_field == "vec"
    assert cfg.primary_field == "row_id"
    assert cfg.metadata_field == "meta"
    assert cfg.vidx_name == "custom_vidx"


def test_seekdb_config_reads_SEEKDB_sparse_and_hybrid_aliases(monkeypatch):
    monkeypatch.delenv("SEEKDB_POOL_RECYCLE", raising=False)
    monkeypatch.delenv("SEEKDB_POOL_PRE_PING", raising=False)
    monkeypatch.setenv("SEEKDB_INCLUDE_SPARSE", "true")
    # SEEKDB_ENABLE_NATIVE_HYBRID defaults to True; explicitly disable to
    # prove the alias does bind.
    monkeypatch.setenv("SEEKDB_ENABLE_NATIVE_HYBRID", "false")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.include_sparse is True
    assert cfg.enable_native_hybrid is False


def test_seekdb_rejects_SEEKDB_POOL_RECYCLE_env(monkeypatch):
    """Pool tuning is a no-op in embedded mode; setting it should fail loudly."""
    monkeypatch.setenv("SEEKDB_POOL_RECYCLE", "1800")

    from powermem.storage.config.oceanbase import SeekDBConfig

    with pytest.raises(ValueError, match="SEEKDB_POOL_RECYCLE"):
        SeekDBConfig()


def test_seekdb_rejects_SEEKDB_POOL_PRE_PING_env(monkeypatch):
    monkeypatch.setenv("SEEKDB_POOL_PRE_PING", "false")

    from powermem.storage.config.oceanbase import SeekDBConfig

    with pytest.raises(ValueError, match="SEEKDB_POOL_PRE_PING"):
        SeekDBConfig()


def test_seekdb_native_hybrid_defaults_to_true(monkeypatch):
    """SEEKDB_ENABLE_NATIVE_HYBRID defaults to True (seekdb ≥1.3)."""
    monkeypatch.delenv("SEEKDB_ENABLE_NATIVE_HYBRID", raising=False)
    monkeypatch.delenv("OCEANBASE_ENABLE_NATIVE_HYBRID", raising=False)

    from powermem.storage.config.oceanbase import SeekDBConfig

    assert SeekDBConfig().enable_native_hybrid is True


# ---------------------------------------------------------------------------
# Namespace isolation: SeekDBConfig must NOT read OCEANBASE_* env vars.
# ---------------------------------------------------------------------------


def test_seekdb_config_ignores_OCEANBASE_env_vars(monkeypatch):
    """OCEANBASE_* keys are reserved for the oceanbase provider; SeekDBConfig
    must not bleed them in.
    """
    monkeypatch.delenv("SEEKDB_PATH", raising=False)
    monkeypatch.delenv("SEEKDB_DATABASE", raising=False)
    monkeypatch.delenv("SEEKDB_TEXT_FIELD", raising=False)
    monkeypatch.delenv("SEEKDB_POOL_RECYCLE", raising=False)
    monkeypatch.setenv("OCEANBASE_PATH", "/should/not/leak")
    monkeypatch.setenv("OCEANBASE_DATABASE", "leaked_db")
    monkeypatch.setenv("OCEANBASE_TEXT_FIELD", "leaked_doc")
    monkeypatch.setenv("OCEANBASE_POOL_RECYCLE", "9999")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.ob_path == "./seekdb_data"        # default, not the OCEANBASE_ value
    assert cfg.db_name == "test"                  # default
    assert cfg.text_field == "document"           # default
    assert cfg.pool_recycle == 3600               # default


# ---------------------------------------------------------------------------
# OceanBase host required + OCEANBASE_PATH rejection.
# ---------------------------------------------------------------------------


def test_oceanbase_default_host_is_127_0_0_1(monkeypatch):
    monkeypatch.delenv("OCEANBASE_HOST", raising=False)
    monkeypatch.delenv("OCEANBASE_PATH", raising=False)

    from powermem.storage.config.oceanbase import OceanBaseConfig

    assert OceanBaseConfig().host == "127.0.0.1"


def test_oceanbase_rejects_empty_host(monkeypatch):
    monkeypatch.delenv("OCEANBASE_PATH", raising=False)

    from powermem.storage.config.oceanbase import OceanBaseConfig

    with pytest.raises(ValueError, match="OCEANBASE_HOST"):
        OceanBaseConfig(host="")


def test_oceanbase_rejects_OCEANBASE_PATH_env(monkeypatch):
    """Setting OCEANBASE_PATH while using DATABASE_PROVIDER=oceanbase is a
    config error — that env var is the seekdb on-disk path, not a remote
    cluster setting.
    """
    monkeypatch.setenv("OCEANBASE_PATH", "/some/seekdb/dir")

    from powermem.storage.config.oceanbase import OceanBaseConfig

    with pytest.raises(ValueError, match="OCEANBASE_PATH"):
        OceanBaseConfig()


def test_seekdb_config_unaffected_by_OCEANBASE_PATH_env_rejection(monkeypatch):
    """The OCEANBASE_PATH-rejection model_validator on OceanBaseConfig must
    NOT fire for the SeekDBConfig subclass — for seekdb, that env var is
    ignored (per namespace isolation) and embedded mode keeps working.
    """
    monkeypatch.setenv("OCEANBASE_PATH", "/some/seekdb/dir")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()  # must not raise
    # OCEANBASE_PATH is ignored — seekdb uses its own SEEKDB_PATH default.
    assert cfg.ob_path == "./seekdb_data"


# ---------------------------------------------------------------------------
# Zero-config MemoryConfig + DatabaseSettings defaults.
# ---------------------------------------------------------------------------


def test_memory_config_default_storage_is_seekdb(monkeypatch):
    """The headline zero-config-default contract."""
    monkeypatch.delenv("DATABASE_PROVIDER", raising=False)
    monkeypatch.delenv("OCEANBASE_HOST", raising=False)
    monkeypatch.delenv("SEEKDB_HOST", raising=False)
    monkeypatch.delenv("OCEANBASE_PATH", raising=False)

    from powermem.configs import MemoryConfig
    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = MemoryConfig()

    assert isinstance(cfg.vector_store, SeekDBConfig)
    assert cfg.vector_store._provider_name == "seekdb"
    assert cfg.vector_store.host == ""  # embedded mode


def test_database_settings_default_provider_is_seekdb(monkeypatch):
    monkeypatch.delenv("DATABASE_PROVIDER", raising=False)

    from powermem.config_loader import DatabaseSettings

    assert DatabaseSettings().provider == "seekdb"
