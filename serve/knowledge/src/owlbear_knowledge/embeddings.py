"""Embedding generation — protocol + BGE-M3 adapter."""

from __future__ import annotations

import gc
import os
import ssl
import threading
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from owlbear_knowledge.protocols.failures import (
    KnowledgeFailure,
    KnowledgeFailureStage,
    KnowledgeOperationError,
)


class SparseVector(BaseModel):
    """Sparse vector representation for lexical matching."""

    indices: list[int]
    values: list[float]


class HybridEmbedding(BaseModel):
    """Multi-representation embedding used by hybrid retrieval."""

    dense: list[float]
    sparse: SparseVector | None = None
    colbert: list[list[float]] | None = None


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for batch embedding providers."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


def _configure_huggingface_tls() -> None:
    """Bridge a Node-style extra CA into Hugging Face's Python HTTP client."""
    if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR"):
        return
    extra_ca = os.environ.get("NODE_EXTRA_CA_CERTS")
    if not extra_ca:
        return
    ca_path = Path(extra_ca).expanduser()
    if not ca_path.is_file() or not os.access(ca_path, os.R_OK):
        return

    import httpx  # noqa: PLC0415
    from huggingface_hub import set_client_factory  # noqa: PLC0415
    from huggingface_hub.utils._http import hf_request_event_hook  # noqa: PLC0415

    context = ssl.create_default_context()
    context.load_verify_locations(cafile=str(ca_path))

    def client_factory() -> httpx.Client:
        return httpx.Client(
            event_hooks={"request": [hf_request_event_hook]},
            follow_redirects=True,
            timeout=None,  # noqa: S113 - preserve Hugging Face's default client contract.
            verify=context,
        )

    set_client_factory(client_factory)


def _model_load_failure(error: Exception) -> KnowledgeOperationError:
    """Convert model setup failures to stable, safe diagnostics."""
    details = str(error).lower()
    configured_ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR")
    if configured_ca and not Path(configured_ca).exists():
        code = "embedding_tls_configuration"
        message = "BGE-M3 TLS configuration is unavailable"
    elif "certificate" in details or "certificate_verify_failed" in details or "ssl" in details or "tls" in details:
        code = "embedding_tls_failed"
        message = "BGE-M3 download TLS verification failed"
    elif "localentrynotfound" in details or "local entry" in details or "no local model" in details:
        code = "embedding_model_unavailable"
        message = "BGE-M3 model is unavailable locally"
    else:
        code = "embedding_download_failed"
        message = "BGE-M3 model download failed"
    return KnowledgeOperationError(
        KnowledgeFailure(
            stage=KnowledgeFailureStage.INDEXING,
            code=code,
            retryable=True,
            message=message,
        )
    )


class BgeM3EmbeddingProvider:
    """Embedding provider backed by ``FlagEmbedding.BGEM3FlagModel``.

    The model is lazily loaded on first use and can be released via
    :meth:`unload`. :meth:`embed` satisfies :class:`EmbeddingProvider`
    (dense only). :meth:`embed_hybrid` returns full HybridEmbedding objects.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 16,
        idle_timeout: float = 600.0,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.idle_timeout = float(idle_timeout)
        self._model: object | None = None
        self._last_used: float = 0.0
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> object:
        """Lazily create the BGEM3FlagModel instance.

        Raises ImportError with an actionable message when FlagEmbedding
        is not installed.
        """
        with self._lock:
            if self._model is None:
                try:
                    from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415
                except ImportError:
                    raise KnowledgeOperationError(
                        KnowledgeFailure(
                            stage=KnowledgeFailureStage.INDEXING,
                            code="embedding_dependency_missing",
                            retryable=False,
                            message="FlagEmbedding dependency is unavailable",
                        )
                    ) from None
                _configure_huggingface_tls()
                try:
                    self._model = BGEM3FlagModel(
                        self.model_name,
                        use_fp16=True,
                        devices=["cpu"],
                        batch_size=self.batch_size,
                    )
                except KnowledgeOperationError:
                    raise
                except Exception as exc:
                    raise _model_load_failure(exc) from exc
        return self._model

    def _reset_timer(self) -> None:
        if self.idle_timeout <= 0:
            return
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.idle_timeout, self.unload)
            self._timer.daemon = True
            self._timer.start()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts, returning dense vectors only (1024-d).

        Returns an empty list when *texts* is empty (no model loaded).
        """
        if not texts:
            return []
        model = self._ensure_model()
        self._last_used = time.monotonic()
        self._reset_timer()
        output = model.encode(texts)  # type: ignore[union-attr]
        return [row.tolist() for row in output["dense_vecs"]]

    def embed_hybrid(self, texts: list[str]) -> list[HybridEmbedding]:
        """Embed texts, returning full hybrid embeddings.

        Returns an empty list when *texts* is empty (no model loaded).
        """
        if not texts:
            return []

        model = self._ensure_model()
        self._last_used = time.monotonic()
        self._reset_timer()
        output = model.encode(texts, return_sparse=True, return_colbert_vecs=True)  # type: ignore[union-attr]

        results: list[HybridEmbedding] = []
        for i in range(len(texts)):
            dense = output["dense_vecs"][i].tolist()
            lex = output["lexical_weights"][i]
            sparse = SparseVector(
                indices=[int(k) for k in lex],
                values=list(lex.values()),
            )
            colbert = output["colbert_vecs"][i].tolist()
            results.append(HybridEmbedding(dense=dense, sparse=sparse, colbert=colbert))
        return results

    def unload(self) -> None:
        """Release the model and reclaim memory."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._model = None
        gc.collect()
