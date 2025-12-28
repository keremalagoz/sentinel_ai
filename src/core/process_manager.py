from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from datetime import datetime
import os


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
        
        self._process.readyReadStandardOutput.connect(self._handle_stdout)
        self._process.readyReadStandardError.connect(self._handle_stderr)
        self._process.finished.connect(self._handle_finished)
    
    def start_process(self, command: str, args: list, requires_root: bool = False):
        """
        Komutu başlatır ve log dosyası oluşturur.
        
        requires_root: True ise komutun başına pkexec eklenir (Linux yetki yükseltme)
        """
        if requires_root:
            args = [command] + args
            command = "pkexec"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = os.path.join("temp", f"session_{timestamp}.txt")
        
        os.makedirs("temp", exist_ok=True)
        self._log_file = open(self._log_path, "a", encoding="utf-8")
        
        self._log_file.write(f"[SESSION START] {datetime.now().isoformat()}\n")
        self._log_file.write(f"[COMMAND] {command} {' '.join(args)}\n")
        self._log_file.write("-" * 50 + "\n")
        self._log_file.flush()
        
        self._process.start(command, args)
    
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

