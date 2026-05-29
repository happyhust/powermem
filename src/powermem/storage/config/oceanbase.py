import os
from typing import Any, ClassVar, Dict, Optional

from pydantic import AliasChoices, Field, field_validator, model_validator
from powermem.settings import settings_config

from powermem.storage.config.base import BaseVectorStoreConfig, BaseGraphStoreConfig


class OceanBaseConfig(BaseVectorStoreConfig):
    """Configuration for a remote OceanBase cluster.

    This provider always talks to an actual OceanBase server — there is no
    embedded / on-disk mode here. The ``OCEANBASE_PATH`` env var is **not
    accepted** on this provider; use ``DATABASE_PROVIDER=seekdb`` (and
    ``SEEKDB_PATH``) for embedded mode instead.
    """

    _provider_name = "oceanbase"
    _class_path = "powermem.storage.oceanbase.oceanbase.OceanBaseVectorStore"

    try:
        from pyobvector import ObVecClient
    except ImportError:
        raise ImportError("The 'pyobvector' library is required. Please install it using 'pip install pyobvector'.")
    ObVecClient: ClassVar[type] = ObVecClient

    model_config = settings_config("VECTOR_STORE_", extra="forbid", env_file=None)

    collection_name: str = Field(
        default="power_mem",
        validation_alias=AliasChoices(
            "collection_name",
            "VECTOR_STORE_COLLECTION_NAME",
            "OCEANBASE_COLLECTION",
        ),
        description="Default name for the collection"
    )

    # Connection parameters
    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices(
            "host",
            "OCEANBASE_HOST",
        ),
        description=(
            "OceanBase server host. Required; must be non-empty. For embedded "
            "on-disk storage, use DATABASE_PROVIDER=seekdb instead."
        ),
    )

    @field_validator("host", mode="after")
    @classmethod
    def _host_must_be_nonempty(cls, value: str) -> str:
        # Inherited validators run on subclasses by default; SeekDBConfig
        # legitimately allows an empty host (= embedded mode), so the
        # non-empty check only fires on the direct OceanBaseConfig class.
        if cls.__name__ != "OceanBaseConfig":
            return value
        if not value or not value.strip():
            raise ValueError(
                "OCEANBASE_HOST must be non-empty when DATABASE_PROVIDER=oceanbase. "
                "Use DATABASE_PROVIDER=seekdb for embedded on-disk storage."
            )
        return value

    @model_validator(mode="after")
    def _reject_oceanbase_path_env(self):
        # OCEANBASE_PATH is a seekdb concept (the on-disk data directory).
        # SeekDBConfig (subclass) keeps it as a valid fallback alias for
        # SEEKDB_PATH; the OceanBase remote-cluster provider rejects it so
        # users don't silently get embedded-mode behaviour from a misnamed env.
        if type(self) is OceanBaseConfig and os.environ.get("OCEANBASE_PATH"):
            raise ValueError(
                "OCEANBASE_PATH is not accepted when DATABASE_PROVIDER=oceanbase. "
                "Unset it, or switch to DATABASE_PROVIDER=seekdb (with SEEKDB_PATH) "
                "for embedded on-disk storage."
            )
        return self


    port: str = Field(
        default="2881",
        validation_alias=AliasChoices(
            "port",
            "OCEANBASE_PORT",
        ),
        description="OceanBase server port"
    )

    @field_validator("port", mode="before")
    @classmethod
    def _coerce_port_to_str(cls, value: Any) -> Any:
        if isinstance(value, int):
            return str(value)
        return value

    user: str = Field(
        default="root@test",
        validation_alias=AliasChoices(
            "OCEANBASE_USER",
            "user", # avoid using system USER environment variable first
        ),
        description="OceanBase username"
    )
    
    password: str = Field(
        default="",
        validation_alias=AliasChoices(
            "password",
            "OCEANBASE_PASSWORD",
        ),
        description="OceanBase password"
    )
    
    db_name: str = Field(
        default="test",
        validation_alias=AliasChoices(
            "db_name",
            "OCEANBASE_DATABASE",
        ),
        description="OceanBase database name"
    )

    connection_args: Optional[dict] = Field(
        default=None,
        validation_alias=AliasChoices(
            "connection_args",
        ),
        description="OceanBase connection args"
    )

    # Connection pool parameters
    pool_recycle: int = Field(
        default=3600,
        validation_alias=AliasChoices(
            "pool_recycle",
            "OCEANBASE_POOL_RECYCLE",
        ),
        description="SQLAlchemy pool_recycle in seconds (prevents stale connections)"
    )

    pool_pre_ping: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "pool_pre_ping",
            "OCEANBASE_POOL_PRE_PING",
        ),
        description="SQLAlchemy pool_pre_ping (tests connections before use)"
    )

    # Vector index parameters
    index_type: str = Field(
        default="HNSW",
        validation_alias=AliasChoices(
            "index_type",
            "OCEANBASE_INDEX_TYPE",
        ),
        description="Type of vector index (HNSW, IVF, FLAT, etc.)"
    )
    
    vidx_metric_type: str = Field(
        default="l2",
        validation_alias=AliasChoices(
            "vidx_metric_type",
            "OCEANBASE_VECTOR_METRIC_TYPE",
        ),
        description="Distance metric (l2, inner_product, cosine)"
    )
    
    embedding_model_dims: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "embedding_model_dims",
            "OCEANBASE_EMBEDDING_MODEL_DIMS",
        ),
        description="Dimension of vectors"
    )

    # Advanced parameters
    vidx_algo_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Index algorithm parameters"
    )
    
    normalize: bool = Field(
        default=False,
        description="Whether to normalize vectors"
    )
    
    include_sparse: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "include_sparse",
            "OCEANBASE_INCLUDE_SPARSE",
            "SPARSE_VECTOR_ENABLE",
        ),
        description="Whether to include sparse vector support"
    )
    
    hybrid_search: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "hybrid_search",
        ),
        description="Whether to enable hybrid search"
    )

    enable_native_hybrid: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "enable_native_hybrid",
            "OCEANBASE_ENABLE_NATIVE_HYBRID",
        ),
        description="Whether to enable OceanBase native hybrid search"
    )
    
    auto_configure_vector_index: bool = Field(
        default=True,
        description="Whether to automatically configure vector index settings"
    )

    # Fulltext search parameters
    fulltext_parser: str = Field(
        default="ik",
        description="Fulltext parser type (ik, ngram, ngram2, beng, space)"
    )

    # Field names
    primary_field: str = Field(
        default="id",
        validation_alias=AliasChoices(
            "primary_field",
            "OCEANBASE_PRIMARY_FIELD",
        ),
        description="Primary key field name"
    )
    
    vector_field: str = Field(
        default="embedding",
        validation_alias=AliasChoices(
            "vector_field",
            "OCEANBASE_VECTOR_FIELD",
        ),
        description="Vector field name"
    )
    
    text_field: str = Field(
        default="document",
        validation_alias=AliasChoices(
            "text_field",
            "OCEANBASE_TEXT_FIELD",
        ),
        description="Text field name"
    )
    
    metadata_field: str = Field(
        default="metadata",
        validation_alias=AliasChoices(
            "metadata_field",
            "OCEANBASE_METADATA_FIELD",
        ),
        description="Metadata field name"
    )
    
    vidx_name: str = Field(
        default="vidx",
        validation_alias=AliasChoices(
            "vidx_name",
            "OCEANBASE_VIDX_NAME",
        ),
        description="Vector index name"
    )

    vector_weight: float = Field(
        default=0.5,
        description="Weight for vector search"
    )
    
    fts_weight: float = Field(
        default=0.5,
        description="Weight for fulltext search"
    )
    
    sparse_weight: Optional[float] = Field(
        default=None,
        description="Weight for sparse vector search"
    )
    
    reranker: Optional[Any] = Field(
        default=None,
        description="Reranker model for fine ranking in hybrid search"
    )



class OceanBaseGraphConfig(BaseGraphStoreConfig):
    """Configuration for OceanBase graph store."""

    _provider_name = "oceanbase"
    _class_path = "powermem.storage.oceanbase.oceanbase_graph.MemoryGraph"

    model_config = settings_config("GRAPH_STORE_", extra="forbid", env_file=None)

    # All fields (connection, vector, max_hops) are inherited from BaseGraphStoreConfig
    # No additional fields needed for OceanBase GraphStore at this time


class SeekDBConfig(OceanBaseConfig):
    """Configuration for embedded seekdb vector store.

    seekdb is OceanBase's embedded mode: same engine, same SQL surface, same
    Python backend class — just no separate database server. Use this provider
    when you want zero-ops local storage; use ``oceanbase`` when you point at a
    remote OceanBase cluster.

    **Namespace isolation:** ``SeekDBConfig`` reads only ``SEEKDB_*`` env
    variables (plus the generic ``VECTOR_STORE_*`` / ``SPARSE_VECTOR_ENABLE``
    feature toggles). It deliberately does NOT fall back to ``OCEANBASE_*``
    keys — that namespace is reserved for the remote-cluster provider. This
    keeps a seekdb-named ``.env`` self-contained and makes the operative
    config obvious from the keys alone.
    """

    _provider_name = "seekdb"
    # Same backend class as OceanBase — seekdb is OceanBase running embedded.
    _class_path = "powermem.storage.oceanbase.oceanbase.OceanBaseVectorStore"

    model_config = settings_config("VECTOR_STORE_", extra="forbid", env_file=None)

    collection_name: str = Field(
        default="power_mem",
        validation_alias=AliasChoices(
            "collection_name",
            "VECTOR_STORE_COLLECTION_NAME",
            "SEEKDB_COLLECTION",
        ),
        description="Default name for the collection",
    )

    host: str = Field(
        default="",
        validation_alias=AliasChoices(
            "host",
            "SEEKDB_HOST",
        ),
        description=(
            "Database server host. Leave empty (default) for embedded seekdb; "
            "set to a hostname only if you are pointing at a remote OceanBase "
            "cluster from a seekdb-named config."
        ),
    )

    ob_path: str = Field(
        default="./seekdb_data",
        validation_alias=AliasChoices(
            "ob_path",
            "SEEKDB_PATH",
        ),
        description="On-disk directory for embedded seekdb data files",
    )

    port: str = Field(
        default="2881",
        validation_alias=AliasChoices(
            "port",
            "SEEKDB_PORT",
        ),
        description="Database server port (ignored in embedded mode)",
    )

    user: str = Field(
        default="root@test",
        validation_alias=AliasChoices(
            "SEEKDB_USER",
            "user",  # avoid using system USER environment variable first
        ),
        description="Database username (ignored in embedded mode)",
    )

    password: str = Field(
        default="",
        validation_alias=AliasChoices(
            "password",
            "SEEKDB_PASSWORD",
        ),
        description="Database password (ignored in embedded mode)",
    )

    db_name: str = Field(
        default="test",
        validation_alias=AliasChoices(
            "db_name",
            "SEEKDB_DATABASE",
        ),
        description="Database name",
    )

    index_type: str = Field(
        default="HNSW",
        validation_alias=AliasChoices(
            "index_type",
            "SEEKDB_INDEX_TYPE",
        ),
        description="Type of vector index (HNSW, IVF, FLAT, etc.)",
    )

    vidx_metric_type: str = Field(
        default="l2",
        validation_alias=AliasChoices(
            "vidx_metric_type",
            "SEEKDB_VECTOR_METRIC_TYPE",
        ),
        description="Distance metric (l2, inner_product, cosine)",
    )

    embedding_model_dims: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "embedding_model_dims",
            "SEEKDB_EMBEDDING_MODEL_DIMS",
        ),
        description="Dimension of vectors",
    )

    # --- Schema-shape fields ------------------------------------------------
    # Column names PowerMem reads / writes. SEEKDB_* only — keeps a seekdb-
    # named .env self-contained.
    primary_field: str = Field(
        default="id",
        validation_alias=AliasChoices(
            "primary_field",
            "SEEKDB_PRIMARY_FIELD",
        ),
        description="Primary key field name",
    )

    vector_field: str = Field(
        default="embedding",
        validation_alias=AliasChoices(
            "vector_field",
            "SEEKDB_VECTOR_FIELD",
        ),
        description="Vector column name",
    )

    text_field: str = Field(
        default="document",
        validation_alias=AliasChoices(
            "text_field",
            "SEEKDB_TEXT_FIELD",
        ),
        description="Text column name",
    )

    metadata_field: str = Field(
        default="metadata",
        validation_alias=AliasChoices(
            "metadata_field",
            "SEEKDB_METADATA_FIELD",
        ),
        description="Metadata column name",
    )

    vidx_name: str = Field(
        default="vidx",
        validation_alias=AliasChoices(
            "vidx_name",
            "SEEKDB_VIDX_NAME",
        ),
        description="Vector index name",
    )

    # --- Connection pool ----------------------------------------------------
    # Only meaningful when seekdb is pointed at a remote host. In embedded
    # mode the backend uses a NullPool (single-threaded engine) so these are
    # effectively no-ops.
    pool_recycle: int = Field(
        default=3600,
        validation_alias=AliasChoices(
            "pool_recycle",
            "SEEKDB_POOL_RECYCLE",
        ),
        description=(
            "SQLAlchemy pool_recycle in seconds (prevents stale connections). "
            "No-op in embedded mode."
        ),
    )

    pool_pre_ping: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "pool_pre_ping",
            "SEEKDB_POOL_PRE_PING",
        ),
        description=(
            "SQLAlchemy pool_pre_ping (tests connections before use). "
            "No-op in embedded mode."
        ),
    )

    # --- Hybrid / sparse retrieval toggles ----------------------------------
    # SPARSE_VECTOR_ENABLE is a generic feature toggle (not OceanBase-
    # namespaced) so it is shared by all providers and kept here.
    include_sparse: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "include_sparse",
            "SEEKDB_INCLUDE_SPARSE",
            "SPARSE_VECTOR_ENABLE",
        ),
        description="Whether to include sparse vector support",
    )

    enable_native_hybrid: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "enable_native_hybrid",
            "SEEKDB_ENABLE_NATIVE_HYBRID",
        ),
        description=(
            "Use the seekdb native hybrid-search SQL extension instead of "
            "the Python-side hybrid pipeline. Enabled by default for seekdb "
            "≥1.3 (the version this branch depends on)."
        ),
    )



class SeekDBGraphConfig(OceanBaseGraphConfig):
    """Configuration for embedded seekdb graph store.

    Shares ``OceanBaseGraphConfig``'s backend (MemoryGraph) and field set; only
    the registered provider name differs so users can write
    ``GRAPH_STORE_PROVIDER=seekdb`` symmetrically with the vector store side.
    """

    _provider_name = "seekdb"
    _class_path = "powermem.storage.oceanbase.oceanbase_graph.MemoryGraph"

    model_config = settings_config("GRAPH_STORE_", extra="forbid", env_file=None)
