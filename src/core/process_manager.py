from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from datetime import datetime
import os
import shlex

from src.core.execution_manager import get_execution_manager, ExecutionMode


class AdvancedProcessManager(QObject):
    """
    Terminal komutlarını QProcess ile çalıştıran motor.
    UI thread'ini bloklamadan asenkron işlem yapar.
    
    QProcess Neden?
    - subprocess.Popen UI'yı bloklar
    - QProcess Qt event loop ile entegre, sinyallerle UI'ya veri aktarır
    """
    
    sig_output_stream = pyqtSignal(str, str)
    sig_process_finished = pyqtSignal(int, str)
    sig_auth_failed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._log_file = None
        self._log_path = ""
        self._exec_mgr = get_execution_manager()
        
        self._process.readyReadStandardOutput.connect(self._handle_stdout)
        self._process.readyReadStandardError.connect(self._handle_stderr)
        self._process.finished.connect(self._handle_finished)
    
    def start_process(self, command: str, args: list, requires_root: bool = False):
        """
        Komutu ExecutionManager ile hazırlayıp çalıştırır.
        Moda göre (Docker/Native) otomatik ayarlanır.
        """
        # 1. Komutu hazırla (Docker prefix, pkexec vb.)
        final_cmd, final_args, temp_root = self._exec_mgr.prepare_command(
            command, args, requires_root
        )
        
        # 2. Log dosyasını hazırla
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = self._exec_mgr.get_temp_path(f"session_{timestamp}.txt")
        
        try:
            # Dosya yazılabilir mi (Native modda)?
            # Docker modunda container içinde yazdığı için buradaki self._log_file açamayabiliriz
            # Bu yüzden loglamayı sadece Native mod veya Host path ise yapmalıyız.
            
            # Windows/Linux host path ise
            if self._exec_mgr.mode == ExecutionMode.NATIVE:
                log_dir = os.path.dirname(self._log_path)
                os.makedirs(log_dir, exist_ok=True)
                self._log_file = open(self._log_path, "a", encoding="utf-8")
                
                self._log_file.write(f"[SESSION START] {datetime.now().isoformat()}\n")
                self._log_file.write(f"[MODE] {self._exec_mgr.mode.value.upper()}\n")
                self._log_file.write(f"[COMMAND] {final_cmd} {shlex.join(final_args)}\n")
                self._log_file.write("-" * 50 + "\n")
                self._log_file.flush()
        except Exception as e:
            print(f"Log error: {e}")
        
        # 3. Çalıştır
        self._process.start(final_cmd, final_args)
    
    def write_input(self, text: str):
        """
        Çalışan process'e interaktif girdi gönderir.
        Örn: Kullanıcı "y" veya "n" girdisi.
        
        Kritik: Sonuna \n eklenmeli (Enter tuşu simülasyonu)
        """
        if self._process.state() == QProcess.ProcessState.Running:
            data = (text + "\n").encode("utf-8")
            self._process.write(data)
            
            if self._log_file:
                self._log_file.write(f"[INPUT] {text}\n")
                self._log_file.flush()
    
    def stop_process(self):
        """Process'i hızlıca durdurur."""
        if self._process.state() == QProcess.ProcessState.Running:
            self._process.kill()
            self._process.waitForFinished(500)
    
    def _handle_stdout(self):
        """
        Standart çıktıyı okur ve sinyalle yayınlar.
        
        Encoding: UTF-8 ile decode, hatalı karakterler replace edilir.
        Nmap gibi araçlar bazen garip karakterler üretir.
        """
        data = self._process.readAllStandardOutput()
        text = data.data().decode("utf-8", errors="replace")
        
        self.sig_output_stream.emit(text, "stdout")
        
        if self._log_file:
            self._log_file.write(text)
            self._log_file.flush()
    
    def _handle_stderr(self):
        """Hata çıktısını okur ve sinyalle yayınlar."""
        data = self._process.readAllStandardError()
        text = data.data().decode("utf-8", errors="replace")
        
        self.sig_output_stream.emit(text, "stderr")
        
        if self._log_file:
            self._log_file.write(f"[STDERR] {text}")
            self._log_file.flush()
    
    def _handle_finished(self, exit_code: int, exit_status):
        """
        Process bittiğinde çağrılır.
        
        Exit kodları:
        - 0: Başarılı
        - 126/127: Yetki reddi (pkexec iptal)
        """
        if self._log_file:
            self._log_file.write("-" * 50 + "\n")
            self._log_file.write(f"[SESSION END] Exit Code: {exit_code}\n")
            self._log_file.close()
            self._log_file = None
        
        if exit_code in (126, 127):
            self.sig_auth_failed.emit()
        
        self.sig_process_finished.emit(exit_code, self._log_path)
    
    def is_running(self) -> bool:
        """Process çalışıyor mu kontrol eder."""
        return self._process.state() == QProcess.ProcessState.Running

