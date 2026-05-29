"""Tests for the seekdb default vector store registration and zero-config wiring.

seekdb is OceanBase's embedded mode — same backend class, same SQL surface,
only configuration differs. These tests pin that contract:

  - the ``seekdb`` provider routes to ``OceanBaseVectorStore``
  - ``SeekDBConfig()`` boots in embedded mode (no host, on-disk ``ob_path``)
  - ``MemoryConfig()`` with no env vars picks ``seekdb`` as the default
  - ``DatabaseSettings`` reads ``seekdb`` as its default provider
"""

from __future__ import annotations


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
    """Schema-shape fields (column/index names) must also accept SEEKDB_*.

    Without these aliases users have to mix SEEKDB_* and OCEANBASE_* keys in
    the same .env to fully configure seekdb — exactly the asymmetry we want
    to avoid.
    """
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


def test_seekdb_config_falls_back_to_OCEANBASE_schema_shape_aliases(monkeypatch):
    """OCEANBASE_* must still work for users migrating an existing .env."""
    monkeypatch.delenv("SEEKDB_TEXT_FIELD", raising=False)
    monkeypatch.delenv("SEEKDB_VECTOR_FIELD", raising=False)
    monkeypatch.setenv("OCEANBASE_TEXT_FIELD", "legacy_doc")
    monkeypatch.setenv("OCEANBASE_VECTOR_FIELD", "legacy_vec")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.text_field == "legacy_doc"
    assert cfg.vector_field == "legacy_vec"


def test_seekdb_config_reads_SEEKDB_pool_and_hybrid_aliases(monkeypatch):
    """Pool tuning, sparse toggle, and native hybrid switch all accept
    SEEKDB_* — closes the last gap with OCEANBASE_* parity.
    """
    monkeypatch.setenv("SEEKDB_POOL_RECYCLE", "1800")
    monkeypatch.setenv("SEEKDB_POOL_PRE_PING", "false")
    monkeypatch.setenv("SEEKDB_INCLUDE_SPARSE", "true")
    monkeypatch.setenv("SEEKDB_ENABLE_NATIVE_HYBRID", "true")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.pool_recycle == 1800
    assert cfg.pool_pre_ping is False
    assert cfg.include_sparse is True
    assert cfg.enable_native_hybrid is True


def test_seekdb_config_OCEANBASE_pool_and_hybrid_aliases_still_resolve(monkeypatch):
    """Migration safety: existing OCEANBASE_* keys still resolve under seekdb."""
    monkeypatch.delenv("SEEKDB_POOL_RECYCLE", raising=False)
    monkeypatch.delenv("SEEKDB_INCLUDE_SPARSE", raising=False)
    monkeypatch.setenv("OCEANBASE_POOL_RECYCLE", "7200")
    monkeypatch.setenv("OCEANBASE_INCLUDE_SPARSE", "true")

    from powermem.storage.config.oceanbase import SeekDBConfig

    cfg = SeekDBConfig()
    assert cfg.pool_recycle == 7200
    assert cfg.include_sparse is True


def test_memory_config_default_storage_is_seekdb(monkeypatch):
    """The headline #-> seekdb-default contract for zero-config startup."""
    monkeypatch.delenv("DATABASE_PROVIDER", raising=False)
    monkeypatch.delenv("OCEANBASE_HOST", raising=False)
    monkeypatch.delenv("SEEKDB_HOST", raising=False)

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
