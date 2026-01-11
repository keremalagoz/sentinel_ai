
from enum import Enum
from typing import Tuple, List, Optional
import os
import platform
import shutil

class ExecutionMode(Enum):
    DOCKER = "docker"      # Container içinde çalıştır (Tercih edilen)
    NATIVE = "native"      # Host'ta direkt çalıştır (Linux/Windows)

class ExecutionManager:
    """
    Çalıştırma modunu yöneten ve komutları normalize eden merkezi sınıf.
    
    Özellikler:
    - Docker tespiti ve önceliklendirmesi
    - İşletim sistemi tespiti (Windows/Linux)
    - Yetki yönetimi (pkexec vs sudo vs none)
    - Geçici dosya yolu yönetimi (/tmp vs /app/output)
    """
    import time
    
    def __init__(self):
        self._platform = platform.system()  # 'Linux', 'Windows', 'Darwin'
        self._mode = ExecutionMode.NATIVE # Varsayılan başla, ilk çağrıda güncellenir
        self._last_check = 0
        self._check_ttl = 5.0 # 5 saniyede bir docker kontrolü yap
        
        # İlk tespiti hemen yap
        self._update_mode()
        
    @property
    def mode(self) -> ExecutionMode:
        # Getter çağrıldığında TTL kontrolü yap
        if (self._time.time() - self._last_check) > self._check_ttl:
            self._update_mode()
        return self._mode
    
    @property
    def _time(self):
        import time
        return time
    
    @property
    def is_linux(self) -> bool:
        return self._platform == "Linux"
        
    @property
    def is_windows(self) -> bool:
        return self._platform == "Windows"
    
    def _update_mode(self):
        """Modu günceller ve zaman damgasını yeniler"""
        self._mode = self._detect_mode()
        self._last_check = self._time.time()

    def _detect_mode(self) -> ExecutionMode:
        """
        Çalışma modunu belirler.
        Öncelik: Docker > Native
        """
        # Döngüsel importu önlemek için fonksiyon içinde import ediyoruz
        try:
            from src.core.docker_runner import is_container_running
            if is_container_running():
                return ExecutionMode.DOCKER
        except Exception:
            pass
            
        return ExecutionMode.NATIVE
    
    def can_run_privileged(self) -> bool:
        """
        Yüksek yetkili (root) komut çalıştırılabilir mi?
        """
        if self.mode == ExecutionMode.DOCKER:
            return True  # Container içinde zaten root yetkisi var
            
        elif self.is_linux:
            # Linux'ta pkexec var mı?
            return shutil.which("pkexec") is not None
            
        elif self.is_windows:
            # Windows'ta "runas" karmaşık olduğu için şimdilik False dönüyoruz.
            # İleride UAC bypass veya runas entegrasyonu eklenebilir.
            return False
            
        return False
    
    def prepare_command(
        self, 
        tool: str, 
        args: List[str], 
        requires_root: bool = False
    ) -> Tuple[str, List[str], str]:
        """
        Moda göre komutu, argümanları ve çıktı yolunu hazırlar.
        
        Returns:
            (command, normalized_args, temp_output_path_root)
        """
        # Varsayılan (Native) ayarlar
        final_cmd = tool
        final_args = list(args)
        temp_root = "/tmp/" if self.is_linux else os.path.join(os.environ.get("TEMP", "."), "sentinel")
        
        if self.mode == ExecutionMode.DOCKER:
            from src.core.docker_runner import get_docker_command
            
            # Docker için komutu sar
            docker_cmd, docker_args = get_docker_command(tool, args)
            
            final_cmd = docker_cmd
            final_args = docker_args
            temp_root = "/app/output/" # Container içindeki path
            
        elif self.mode == ExecutionMode.NATIVE:
            # Native Linux ve Root gerekli ise
            if requires_root and self.is_linux:
                final_args = [tool] + final_args
                final_cmd = "pkexec"
                
            # Windows ise path ayarla
            if self.is_windows:
                # Windows'ta temp path düzeltmesi
                os.makedirs(temp_root, exist_ok=True)
                
        return (final_cmd, final_args, temp_root)
    
    def get_temp_path(self, filename: str) -> str:
        """
        Moda göre güvenli geçici dosya yolu üretir.
        Örn: /app/output/sentinel_xyz.xml veya C:\Temp\sentinel\sentinel_xyz.xml
        """
        import uuid
        safe_filename = f"sentinel_{uuid.uuid4().hex[:8]}_{filename}"
        
        # Sadece root dizini al, gerisini birleştir
        # prepare_command'i çağırmak yerine mantığı tekrar ediyoruz (basitlik için)
        if self.mode == ExecutionMode.DOCKER:
            return f"/app/output/{safe_filename}"
        elif self.is_linux:
            return f"/tmp/{safe_filename}"
        else:
            # Windows
            base = os.path.join(os.environ.get("TEMP", "."), "sentinel")
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, safe_filename)

# Global instance (Singleton benzeri kullanım için)
_exec_manager = ExecutionManager()

def get_execution_manager() -> ExecutionManager:
    return _exec_manager
