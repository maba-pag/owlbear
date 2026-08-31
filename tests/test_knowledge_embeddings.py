"""Regression tests for Knowledge embedding runtime configuration."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

from owlbear_knowledge.embeddings import _configure_huggingface_tls


def test_configure_huggingface_tls_bridges_node_extra_ca(tmp_path: Path, monkeypatch) -> None:
    ca_path = tmp_path / "corporate-ca.pem"
    ca_path.write_text("certificate", encoding="utf-8")
    monkeypatch.setenv("NODE_EXTRA_CA_CERTS", str(ca_path))
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)

    context = MagicMock()
    client = MagicMock()
    set_client_factory = MagicMock()
    request_hook = object()
    httpx_module = types.ModuleType("httpx")
    httpx_module.Client = client
    huggingface_module = types.ModuleType("huggingface_hub")
    huggingface_module.set_client_factory = set_client_factory
    http_module = types.ModuleType("huggingface_hub.utils._http")
    http_module.hf_request_event_hook = request_hook

    with (
        patch("owlbear_knowledge.embeddings.ssl.create_default_context", return_value=context),
        patch.dict(
            sys.modules,
            {
                "httpx": httpx_module,
                "huggingface_hub": huggingface_module,
                "huggingface_hub.utils": types.ModuleType("huggingface_hub.utils"),
                "huggingface_hub.utils._http": http_module,
            },
        ),
    ):
        _configure_huggingface_tls()

    context.load_verify_locations.assert_called_once_with(cafile=str(ca_path))
    set_client_factory.assert_called_once()
    factory = set_client_factory.call_args.args[0]
    factory()
    client.assert_called_once_with(
        event_hooks={"request": [request_hook]},
        follow_redirects=True,
        timeout=None,
        verify=context,
    )


def test_configure_huggingface_tls_respects_explicit_python_ca(tmp_path: Path, monkeypatch) -> None:
    ca_path = tmp_path / "corporate-ca.pem"
    ca_path.write_text("certificate", encoding="utf-8")
    monkeypatch.setenv("NODE_EXTRA_CA_CERTS", str(ca_path))
    monkeypatch.setenv("SSL_CERT_FILE", str(ca_path))

    with patch("owlbear_knowledge.embeddings.ssl.create_default_context") as create_context:
        _configure_huggingface_tls()

    create_context.assert_not_called()
