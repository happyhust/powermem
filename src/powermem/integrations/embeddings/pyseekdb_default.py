"""Built-in default embedder.

Wraps ``pyseekdb.client.embedding_function.DefaultEmbeddingFunction`` so PowerMem
can start with zero configuration and no external API key. The model is
``sentence-transformers/all-MiniLM-L6-v2`` (384-dim), the same default used by
pyseekdb. It downloads to a local cache on first use and runs locally afterwards.

Override via the ``embedder`` section of :class:`~powermem.configs.MemoryConfig`
to switch to a production-grade provider (OpenAI, Qwen, SiliconFlow, etc.).
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from loguru import logger

from powermem.integrations.embeddings.base import EmbeddingBase
from powermem.integrations.embeddings.config.base import BaseEmbedderConfig

logging.getLogger("onnxruntime").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)


# Match pyseekdb's DefaultEmbeddingFunction so the two systems agree on the
# default model and dimension. Keeping this constant local avoids importing
# pyseekdb at module import time.
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMS = 384


class PyseekdbDefaultEmbedding(EmbeddingBase):
    """Zero-config local embedder backed by pyseekdb's DefaultEmbeddingFunction."""

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)

        try:
            from pyseekdb.client.embedding_function import DefaultEmbeddingFunction
        except ImportError as exc:  # pragma: no cover - pyseekdb is a hard dep
            raise ImportError(
                "pyseekdb is required for the built-in default embedder. "
                "Install it with `pip install pyseekdb`."
            ) from exc

        self._fn = DefaultEmbeddingFunction()
        self.config.model = self.config.model or DEFAULT_MODEL_NAME
        self.config.embedding_dims = (
            self.config.embedding_dims or DEFAULT_EMBEDDING_DIMS
        )

        logger.info(
            "PyseekdbDefaultEmbedding ready (model={}, dims={})",
            self.config.model,
            self.config.embedding_dims,
        )

    def embed(
        self,
        text,
        memory_action: Optional[Literal["add", "search", "update"]] = None,
    ):
        """Return a single embedding vector for ``text``."""
        del memory_action  # unused: default embedder treats all actions identically
        if text is None:
            raise ValueError("text must not be None")
        embeddings = self._fn([text] if isinstance(text, str) else list(text))
        if not embeddings:
            raise RuntimeError("default embedder returned no vectors")
        return list(embeddings[0])

    def embed_batch(
        self,
        texts: List[str],
        memory_action: Optional[Literal["add", "search", "update"]] = None,
    ) -> List[List[float]]:
        """Batch embedding using the underlying ONNX model directly."""
        del memory_action  # unused: default embedder treats all actions identically
        if not texts:
            return []
        return [list(vec) for vec in self._fn(list(texts))]
