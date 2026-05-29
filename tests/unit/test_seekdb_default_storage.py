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
