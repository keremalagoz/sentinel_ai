from datetime import datetime
import os
import shlex
import subprocess
import threading
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from src.core.execution_manager import ExecutionMode, get_execution_manager
from src.core.platform_utils import CONSOLE_ENCODING, resolve_executable


class AdvancedProcessManager(QObject):
    """
    Execute terminal commands asynchronously for the UI.

    Native Windows execution uses subprocess because QProcess startup is
    unreliable in the current desktop/runtime environment.
    """

    sig_output_stream = pyqtSignal(str, str)
    sig_process_finished = pyqtSignal(int, str)
    sig_auth_failed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._subprocess: Optional[subprocess.Popen] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._watch_thread: Optional[threading.Thread] = None
        self._using_subprocess = False
        self._log_file = None
        self._log_path = ""
        self._correlation_id = ""
        self._exec_mgr = get_execution_manager()

        self._process.readyReadStandardOutput.connect(self._handle_stdout)
        self._process.readyReadStandardError.connect(self._handle_stderr)
        self._process.finished.connect(self._handle_finished)
        self._process.errorOccurred.connect(self._handle_error)

    def start_process(
        self,
        command: str,
        args: list,
        requires_root: bool = False,
        correlation_id: str = "",
    ) -> None:
        """
        Prepare and execute a command according to the active execution mode.
        """
        final_cmd, final_args, temp_root = self._exec_mgr.prepare_command(
            command, args, requires_root
        )
        if self._exec_mgr.mode == ExecutionMode.NATIVE:
            final_cmd = resolve_executable(final_cmd)

        self._correlation_id = correlation_id or ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = self._exec_mgr.get_temp_path(f"session_{timestamp}.txt")
        self._prepare_log_file(final_cmd, final_args)

        if self._should_use_subprocess_backend():
            self._start_subprocess(final_cmd, final_args)
            return

        self._using_subprocess = False
        self._process.start(final_cmd, final_args)

    def write_input(self, text: str) -> None:
        """
        Send interactive input to the currently running process.
        """
        if self._using_subprocess and self._subprocess and self._subprocess.stdin:
            try:
                self._subprocess.stdin.write((text + "\n").encode("utf-8"))
                self._subprocess.stdin.flush()
            except Exception:
                pass
        elif self._process.state() == QProcess.ProcessState.Running:
            self._process.write((text + "\n").encode("utf-8"))

        if self._log_file:
            prefix = f"[INPUT][CID:{self._correlation_id}]" if self._correlation_id else "[INPUT]"
            self._log_file.write(f"{prefix} {text}\n")
            self._log_file.flush()

    def stop_process(self) -> None:
        """Stop the active process quickly."""
        if self._using_subprocess and self._subprocess:
            try:
                self._subprocess.kill()
                self._subprocess.wait(timeout=1)
            except Exception:
                pass
            return

        if self._process.state() == QProcess.ProcessState.Running:
            self._process.kill()
            self._process.waitForFinished(500)

    def _prepare_log_file(self, final_cmd: str, final_args: list) -> None:
        try:
            if self._exec_mgr.mode != ExecutionMode.NATIVE:
                return
            log_dir = os.path.dirname(self._log_path)
            os.makedirs(log_dir, exist_ok=True)
            self._log_file = open(self._log_path, "a", encoding="utf-8")
            self._log_file.write(f"[SESSION START] {datetime.now().isoformat()}\n")
            if self._correlation_id:
                self._log_file.write(f"[CID] {self._correlation_id}\n")
            self._log_file.write(f"[MODE] {self._exec_mgr.mode.value.upper()}\n")
            self._log_file.write(f"[COMMAND] {final_cmd} {shlex.join(final_args)}\n")
            self._log_file.write("-" * 50 + "\n")
            self._log_file.flush()
        except Exception as exc:
            print(f"Log error: {exc}")

    def _should_use_subprocess_backend(self) -> bool:
        return self._exec_mgr.mode == ExecutionMode.NATIVE and self._exec_mgr.is_windows

    def _start_subprocess(self, final_cmd: str, final_args: list) -> None:
        self._using_subprocess = True
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._subprocess = subprocess.Popen(
                [final_cmd, *final_args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                creationflags=creation_flags,
            )
        except Exception as exc:
            self._emit_error_text(
                "Komut bulunamadi veya calistirilamadi. "
                f"Detay: {exc}"
            )
            self._finalize_process(-1)
            return

        self._stdout_thread = threading.Thread(
            target=self._read_subprocess_stream,
            args=(self._subprocess.stdout, "stdout"),
            name="process-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_subprocess_stream,
            args=(self._subprocess.stderr, "stderr"),
            name="process-stderr",
            daemon=True,
        )
        self._watch_thread = threading.Thread(
            target=self._wait_for_subprocess,
            name="process-watch",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        self._watch_thread.start()

    def _read_subprocess_stream(self, stream, channel: str) -> None:
        if stream is None:
            return
        try:
            for chunk in iter(stream.readline, b""):
                if not chunk:
                    break
                text = chunk.decode(CONSOLE_ENCODING, errors="replace")
                self.sig_output_stream.emit(text, channel)
                if self._log_file:
                    if channel == "stderr":
                        self._log_file.write(f"[STDERR] {text}")
                    else:
                        self._log_file.write(text)
                    self._log_file.flush()
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _wait_for_subprocess(self) -> None:
        if self._subprocess is None:
            return
        exit_code = self._subprocess.wait()
        if self._stdout_thread and self._stdout_thread.is_alive():
            self._stdout_thread.join(timeout=1)
        if self._stderr_thread and self._stderr_thread.is_alive():
            self._stderr_thread.join(timeout=1)
        self._finalize_process(exit_code)

    def _finalize_process(self, exit_code: int) -> None:
        if self._log_file:
            self._log_file.write("-" * 50 + "\n")
            self._log_file.write(f"[SESSION END] Exit Code: {exit_code}\n")
            self._log_file.close()
            self._log_file = None

        if exit_code in (126, 127):
            self.sig_auth_failed.emit()

        self.sig_process_finished.emit(exit_code, self._log_path)
        self._correlation_id = ""
        self._subprocess = None
        self._using_subprocess = False

    def _handle_stdout(self) -> None:
        data = self._process.readAllStandardOutput()
        text = data.data().decode(CONSOLE_ENCODING, errors="replace")
        self.sig_output_stream.emit(text, "stdout")

        if self._log_file:
            self._log_file.write(text)
            self._log_file.flush()

    def _handle_stderr(self) -> None:
        data = self._process.readAllStandardError()
        text = data.data().decode(CONSOLE_ENCODING, errors="replace")
        self.sig_output_stream.emit(text, "stderr")

        if self._log_file:
            self._log_file.write(f"[STDERR] {text}")
            self._log_file.flush()

    def _handle_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._finalize_process(exit_code)

    def _handle_error(self, error: QProcess.ProcessError) -> None:
        error_messages = {
            QProcess.ProcessError.FailedToStart: (
                "Komut bulunamadi veya calistirilamadi. "
                "Guvenlik araclari (nmap, nikto, hydra vb.) Docker konteynerinde calisir. "
                "Docker servislerinin ayakta oldugundan emin olun."
            ),
            QProcess.ProcessError.Crashed: "Process beklenmedik sekilde sonlandi",
            QProcess.ProcessError.Timedout: "Process zaman asimina ugradi",
            QProcess.ProcessError.WriteError: "Process'e yazilamadi",
            QProcess.ProcessError.ReadError: "Process'ten okunamadi",
        }
        self._emit_error_text(
            error_messages.get(error, "Bilinmeyen hata")
        )

    def _emit_error_text(self, message: str) -> None:
        error_text = f"[ERROR] QProcess Hatasi: {message}\n"
        self.sig_output_stream.emit(error_text, "stderr")

        if self._log_file:
            self._log_file.write(error_text)
            self._log_file.flush()

    def is_running(self) -> bool:
        """Return whether any process backend is currently active."""
        if self._using_subprocess and self._subprocess:
            return self._subprocess.poll() is None
        return self._process.state() == QProcess.ProcessState.Running
