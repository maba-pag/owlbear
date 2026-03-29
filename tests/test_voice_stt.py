"""Failing RED-phase tests for task #50: Voice addon STT with Moonshine.

Covers:
- SttRunner class with start/stop/close lifecycle (AC 1)
- Lazy MicTranscriber creation on first start() (AC 2)
- Constructor keyword params with defaults: model_arch, language, update_interval (AC 3)
- TranscriptJsonListener subclasses TranscriptEventListener, 4 event methods (AC 4)
- NDJSON output for transcript, partial, error message types (AC 5)
- Thread-safe stdout writes via threading.Lock (AC 6)
- on_error emits error NDJSON to stdout + logs to stderr (AC 7)
- Status ready message emitted after MicTranscriber creation (AC 8)
- stop() delegates to MicTranscriber.stop() (AC 9)
- close() idempotent: safe before start and on multiple calls (AC 10)
- ImportError with actionable message when moonshine-voice absent (AC 11)

All tests fail on current HEAD because
``packages/voice/src/owlbear_voice/stt.py`` does not yet exist.
"""

from __future__ import annotations

import json
import sys
import threading
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from owlbear_voice.stt import SttRunner, TranscriptJsonListener

# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

_FAKE_MODEL_PATH = "/fake/model/path"


def _make_moonshine_module() -> MagicMock:
    """Return a sys.modules-compatible mock for moonshine_voice."""
    mock_arch = MagicMock()
    mock_arch.SMALL_STREAMING = "SMALL_STREAMING"

    mock_module = MagicMock()
    mock_module.ModelArch = mock_arch
    mock_module.get_model_for_language = MagicMock(return_value=_FAKE_MODEL_PATH)
    mock_module.MicTranscriber = MagicMock(return_value=MagicMock())
    # TranscriptEventListener must be a real class so subclass check works
    mock_module.TranscriptEventListener = type("TranscriptEventListener", (), {})
    return mock_module


@pytest.fixture()
def mock_moonshine() -> MagicMock:
    """Inject a mock moonshine_voice into sys.modules for the test duration."""
    module = _make_moonshine_module()
    with patch.dict("sys.modules", {"moonshine_voice": module}):
        yield module


@pytest.fixture()
def captured_stdout(monkeypatch: pytest.MonkeyPatch) -> BytesIO:  # noqa: ARG001
    """Replace sys.stdout so tests can inspect NDJSON writes.

    Patches the ``sys`` binding inside ``owlbear_voice.stt`` (not the global
    ``sys.stdout``) because ``TextIOWrapper.buffer`` is a readonly property
    on Python 3.12+ and cannot be patched via setattr.

    stderr writes look up sys.stderr AT CALL TIME so capsys can capture them.

    The ``monkeypatch`` parameter is kept for signature compatibility but the
    actual patching uses ``unittest.mock.patch.object`` instead.
    """
    import owlbear_voice.stt as _stt  # noqa: PLC0415

    buf = BytesIO()
    mock_buf = MagicMock()
    mock_buf.write = MagicMock(side_effect=buf.write)
    mock_buf.flush = MagicMock()
    mock_sys = MagicMock()
    mock_sys.stdout.buffer = mock_buf

    # Use a dynamic lookup so capsys captures the write (not a saved reference)
    def _dynamic_stderr_write(msg: str) -> None:
        import sys as _cur_sys  # noqa: PLC0415

        _cur_sys.stderr.write(msg)

    mock_sys.stderr.write = MagicMock(side_effect=_dynamic_stderr_write)

    with patch.object(_stt, "sys", mock_sys):
        yield buf


def _read_ndjson(buf: BytesIO) -> list[dict]:
    """Parse all complete JSON lines from buf, skipping blanks."""
    buf.seek(0)
    text = buf.read().decode()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# AC1: SttRunner class with start() / stop() / close() lifecycle methods
# ---------------------------------------------------------------------------


class TestFromAC_SttRunnerClass:
    """SttRunner must exist in owlbear_voice.stt with the three lifecycle methods."""

    def test_stt_runner_is_importable(self) -> None:
        """AC1: SttRunner must be importable from owlbear_voice.stt."""
        assert SttRunner is not None

    def test_has_start_method(self) -> None:
        """AC1: SttRunner must have a callable start() method."""
        assert callable(getattr(SttRunner, "start", None))

    def test_has_stop_method(self) -> None:
        """AC1: SttRunner must have a callable stop() method."""
        assert callable(getattr(SttRunner, "stop", None))

    def test_has_close_method(self) -> None:
        """AC1: SttRunner must have a callable close() method."""
        assert callable(getattr(SttRunner, "close", None))


# ---------------------------------------------------------------------------
# AC2: Lazy MicTranscriber creation — not in __init__, only on first start()
# ---------------------------------------------------------------------------


class TestFromAC_LazyMicTranscriberCreation:
    """MicTranscriber must be created inside start(), never in __init__."""

    def test_mic_transcriber_not_created_in_init(self, mock_moonshine: MagicMock) -> None:
        """AC2: SttRunner() must not call MicTranscriber constructor."""
        SttRunner()
        mock_moonshine.MicTranscriber.assert_not_called()

    def test_get_model_for_language_not_called_in_init(self, mock_moonshine: MagicMock) -> None:
        """AC2: SttRunner() must not call get_model_for_language (no lazy load at init)."""
        SttRunner()
        mock_moonshine.get_model_for_language.assert_not_called()

    def test_mic_transcriber_created_on_first_start(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC2: First call to start() must create MicTranscriber."""
        runner = SttRunner()
        runner.start()
        mock_moonshine.MicTranscriber.assert_called_once()


# ---------------------------------------------------------------------------
# AC3: Constructor keyword params with correct defaults
# ---------------------------------------------------------------------------


class TestFromAC_SttRunnerConstructorParams:
    """SttRunner must accept model_arch, language, update_interval with specified defaults."""

    def test_language_defaults_to_en(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC3: Default language must be 'en', passed to get_model_for_language."""
        runner = SttRunner()
        runner.start()
        call_args = mock_moonshine.get_model_for_language.call_args
        positional_language = call_args.args[0] if call_args.args else None
        kwarg_language = call_args.kwargs.get("language")
        assert positional_language == "en" or kwarg_language == "en"

    def test_update_interval_defaults_to_0_5(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC3: Default update_interval must be 0.5, passed to MicTranscriber."""
        runner = SttRunner()
        runner.start()
        mic_kwargs = mock_moonshine.MicTranscriber.call_args.kwargs
        assert mic_kwargs.get("update_interval") == 0.5  # noqa: PLR2004

    def test_model_arch_defaults_to_small_streaming(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC3: Default model_arch must be ModelArch.SMALL_STREAMING."""
        runner = SttRunner()
        runner.start()
        mic_kwargs = mock_moonshine.MicTranscriber.call_args.kwargs
        assert mic_kwargs.get("model_arch") == mock_moonshine.ModelArch.SMALL_STREAMING

    def test_explicit_language_used_for_model_resolution(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC3: language='fr' kwarg must be forwarded to get_model_for_language."""
        runner = SttRunner(language="fr")
        runner.start()
        call_args = mock_moonshine.get_model_for_language.call_args
        positional_language = call_args.args[0] if call_args.args else None
        kwarg_language = call_args.kwargs.get("language")
        assert positional_language == "fr" or kwarg_language == "fr"

    def test_explicit_update_interval_used_for_mic_transcriber(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC3: update_interval=1.0 kwarg must be forwarded to MicTranscriber."""
        runner = SttRunner(update_interval=1.0)
        runner.start()
        mic_kwargs = mock_moonshine.MicTranscriber.call_args.kwargs
        assert mic_kwargs.get("update_interval") == 1.0  # noqa: PLR2004


# ---------------------------------------------------------------------------
# AC4: TranscriptJsonListener subclasses TranscriptEventListener, 4 event methods
# ---------------------------------------------------------------------------


class TestFromAC_TranscriptJsonListenerStructure:
    """TranscriptJsonListener must have correct inheritance and all 4 event methods."""

    def test_transcript_json_listener_is_importable(self) -> None:
        """AC4: TranscriptJsonListener must be importable from owlbear_voice.stt."""
        assert TranscriptJsonListener is not None

    def test_transcript_json_listener_in_mro_has_transcript_event_listener(self) -> None:
        """AC4: TranscriptJsonListener must subclass moonshine_voice.TranscriptEventListener."""
        mro_names = [cls.__name__ for cls in TranscriptJsonListener.__mro__]
        assert "TranscriptEventListener" in mro_names

    def test_has_on_line_started(self) -> None:
        """AC4: TranscriptJsonListener must implement on_line_started."""
        assert callable(getattr(TranscriptJsonListener, "on_line_started", None))

    def test_has_on_text_changed(self) -> None:
        """AC4: TranscriptJsonListener must implement on_text_changed."""
        assert callable(getattr(TranscriptJsonListener, "on_text_changed", None))

    def test_has_on_line_completed(self) -> None:
        """AC4: TranscriptJsonListener must implement on_line_completed."""
        assert callable(getattr(TranscriptJsonListener, "on_line_completed", None))

    def test_has_on_error(self) -> None:
        """AC4: TranscriptJsonListener must implement on_error."""
        assert callable(getattr(TranscriptJsonListener, "on_error", None))


# ---------------------------------------------------------------------------
# AC5: NDJSON output for transcript, partial, and error message types
# ---------------------------------------------------------------------------


class TestFromAC_NdjsonOutput:
    """TranscriptJsonListener must write valid NDJSON to stdout.buffer for all event types."""

    def test_on_text_changed_emits_partial_type(
        self,
        captured_stdout: BytesIO,
    ) -> None:
        """AC5: on_text_changed must emit JSON with type='partial'."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_text_changed(0, "hello")
        messages = _read_ndjson(captured_stdout)
        assert any(m.get("type") == "partial" for m in messages)

    def test_on_line_completed_emits_transcript_type(
        self,
        captured_stdout: BytesIO,
    ) -> None:
        """AC5: on_line_completed must emit JSON with type='transcript'."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_line_completed(0, "hello world")
        messages = _read_ndjson(captured_stdout)
        assert any(m.get("type") == "transcript" for m in messages)

    def test_on_line_completed_emits_final_true(
        self,
        captured_stdout: BytesIO,
    ) -> None:
        """AC5: on_line_completed transcript message must have final=True."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_line_completed(0, "hello world")
        messages = _read_ndjson(captured_stdout)
        transcripts = [m for m in messages if m.get("type") == "transcript"]
        assert any(m.get("final") is True for m in transcripts)

    def test_on_error_emits_error_type(
        self,
        captured_stdout: BytesIO,
    ) -> None:
        """AC5, AC7: on_error must emit JSON with type='error' to stdout."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_error(Exception("mic error"))
        messages = _read_ndjson(captured_stdout)
        assert any(m.get("type") == "error" for m in messages)

    def test_ndjson_lines_end_with_newline(
        self,
        captured_stdout: BytesIO,
    ) -> None:
        """AC5: Each JSON message written to stdout.buffer must end with b'\\n' (NDJSON)."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_text_changed(0, "test")
        captured_stdout.seek(0)
        raw = captured_stdout.read()
        assert raw.endswith(b"\n")

    def test_ndjson_output_is_valid_json(
        self,
        captured_stdout: BytesIO,
    ) -> None:
        """AC5: stdout output from on_line_completed must be parseable as JSON."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_line_completed(0, "valid json test")
        messages = _read_ndjson(captured_stdout)
        assert len(messages) >= 1
        assert "type" in messages[0]


# ---------------------------------------------------------------------------
# AC6: Thread-safe stdout writes
# ---------------------------------------------------------------------------


class TestFromAC_ThreadSafeStdout:
    """stdout.buffer writes must be guarded by threading.Lock to prevent interleaving."""

    def test_concurrent_callbacks_produce_valid_json_lines(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC6: Concurrent on_text_changed calls must each produce a complete JSON line."""
        lines_received: list[bytes] = []
        partial: list[bytes] = [b""]
        collect_lock = threading.Lock()

        def write_side_effect(data: bytes) -> None:
            with collect_lock:
                partial[0] += data
                if b"\n" in partial[0]:
                    for chunk in partial[0].split(b"\n"):
                        if chunk:
                            lines_received.append(chunk)
                    partial[0] = b""

        mock_buf = MagicMock()
        mock_buf.write = write_side_effect
        mock_buf.flush = MagicMock()
        monkeypatch.setattr(sys.stdout, "buffer", mock_buf)

        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)

        def fire(idx: int) -> None:
            listener.on_text_changed(idx, f"word{idx}")

        threads = [threading.Thread(target=fire, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Every received line must be valid JSON with a type field
        for line in lines_received:
            parsed = json.loads(line.decode())
            assert "type" in parsed

    def test_listener_uses_lock_for_writes(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC6: TranscriptJsonListener constructor accepts a threading.Lock."""
        lock = threading.Lock()
        buf = BytesIO()
        mock_buf = MagicMock()
        mock_buf.write = MagicMock(side_effect=buf.write)
        mock_buf.flush = MagicMock()
        monkeypatch.setattr(sys.stdout, "buffer", mock_buf)

        # Must not raise — listener must accept a lock and use it for writes
        listener = TranscriptJsonListener(lock)
        listener.on_text_changed(0, "locked write")
        mock_buf.write.assert_called()


# ---------------------------------------------------------------------------
# AC7: on_error logs detail to stderr
# ---------------------------------------------------------------------------


class TestFromAC_OnErrorLogsToStderr:
    """on_error must log error detail to stderr in addition to emitting NDJSON on stdout."""

    def test_on_error_writes_exception_detail_to_stderr(
        self,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout writes
        capsys: pytest.CaptureFixture,
    ) -> None:
        """AC7: on_error must log exception message to stderr."""
        lock = threading.Lock()
        listener = TranscriptJsonListener(lock)
        listener.on_error(Exception("stt failure detail"))
        captured = capsys.readouterr()
        assert "stt failure detail" in captured.err


# ---------------------------------------------------------------------------
# AC8: Emits status type='status', state='ready' after MicTranscriber creation
# ---------------------------------------------------------------------------


class TestFromAC_StatusReadyMessage:
    """start() must write a status/ready NDJSON message to stdout after mic is ready."""

    def test_start_emits_status_ready(
        self,
        mock_moonshine: MagicMock,  # noqa: ARG002 — side effect: patches sys.modules for start()
        captured_stdout: BytesIO,
    ) -> None:
        """AC8: start() must emit {type: status, state: ready} after MicTranscriber created."""
        runner = SttRunner()
        runner.start()
        messages = _read_ndjson(captured_stdout)
        status_msgs = [m for m in messages if m.get("type") == "status"]
        assert any(m.get("state") == "ready" for m in status_msgs)


# ---------------------------------------------------------------------------
# AC9: stop() calls MicTranscriber.stop()
# ---------------------------------------------------------------------------


class TestFromAC_StopDelegatesToMicTranscriber:
    """stop() must call MicTranscriber.stop() to trigger LineCompleted for active lines."""

    def test_stop_calls_mic_transcriber_stop(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC9: stop() must call .stop() on the MicTranscriber instance."""
        runner = SttRunner()
        runner.start()
        runner.stop()
        mock_moonshine.MicTranscriber.return_value.stop.assert_called_once()

    def test_stop_before_start_raises_clear_error(self) -> None:
        """AC9: stop() before start() must raise RuntimeError (not an uncaught crash)."""
        runner = SttRunner()
        with pytest.raises((RuntimeError, ValueError)):
            runner.stop()


# ---------------------------------------------------------------------------
# AC10: close() releases resources and is idempotent
# ---------------------------------------------------------------------------


class TestFromAC_CloseIdempotency:
    """close() must release MicTranscriber and be safe to call multiple times or before start."""

    def test_close_before_start_does_not_raise(self) -> None:
        """AC10: close() before start() must not raise."""
        runner = SttRunner()
        runner.close()  # must not raise

    def test_close_multiple_times_does_not_raise(
        self,
        mock_moonshine: MagicMock,  # noqa: ARG002 — side effect: patches sys.modules for start()
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC10: Repeated close() calls must be idempotent."""
        runner = SttRunner()
        runner.start()
        runner.close()
        runner.close()  # second call must not raise

    def test_close_after_start_calls_release_on_mic(
        self,
        mock_moonshine: MagicMock,
        captured_stdout: BytesIO,  # noqa: ARG002 — side effect: suppress stdout from start()
    ) -> None:
        """AC10: close() after start() must release the MicTranscriber instance."""
        runner = SttRunner()
        runner.start()
        runner.close()
        mic_instance = mock_moonshine.MicTranscriber.return_value
        assert mic_instance.close.called or mic_instance.stop.called


# ---------------------------------------------------------------------------
# AC11: ImportError with actionable message when moonshine-voice not installed
# ---------------------------------------------------------------------------


class TestFromAC_ImportErrorWhenMissingMoonshine:
    """start() must raise ImportError with install hint when moonshine-voice is absent."""

    def test_start_raises_import_error(self) -> None:
        """AC11: start() must raise ImportError when moonshine-voice is not installed."""
        with patch.dict("sys.modules", {"moonshine_voice": None}):
            runner = SttRunner()
            with pytest.raises(ImportError):
                runner.start()

    def test_import_error_contains_install_hint(self) -> None:
        """AC11: ImportError message must contain an actionable install instruction."""
        with patch.dict("sys.modules", {"moonshine_voice": None}):
            runner = SttRunner()
            with pytest.raises(ImportError, match=r"uv sync|--extra voice|moonshine.voice|install"):
                runner.start()

    def test_stt_module_importable_without_moonshine_installed(self) -> None:
        """AC11: owlbear_voice.stt must import successfully without moonshine-voice.

        The fact that this test file's top-level import succeeded demonstrates
        that moonshine-voice is NOT imported at stt.py module level (guarded import).
        """
        # If we reach this line, the module-level 'from owlbear_voice.stt import ...'
        # succeeded — confirming guarded import at method level only.
        assert SttRunner is not None
        assert TranscriptJsonListener is not None
