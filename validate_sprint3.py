
import unittest
import os
import sys
import shutil
import time
from datetime import datetime, timedelta

# Proje root'unu ekle
sys.path.insert(0, os.getcwd())

from src.core.execution_manager import get_execution_manager, ExecutionMode
from src.core.cleaner import get_cleaner
from src.core.validators import InputValidator

class TestSprint3(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def tearDown(self):
        pass 

    # =========================================================================
    # 1. Input Validator Testleri
    # =========================================================================
    def test_validator_ip(self):
        print("\n[InputValidator] IP Testi...")
        self.assertTrue(InputValidator.validate_ip("192.168.1.1"))
        self.assertTrue(InputValidator.validate_ip("10.0.0.1/24"))
        self.assertFalse(InputValidator.validate_ip("999.999.999.999"))
        print("[InputValidator] IP Testi: OK")

    def test_validator_injection(self):
        print("\n[InputValidator] Injection Testi...")
        dirty = "127.0.0.1; rm -rf /"
        clean = InputValidator.sanitize(dirty)
        self.assertEqual(clean, "127.0.0.1 rm -rf /")
        
        # Newline kontrolü
        dirty_nl = "127.0.0.1\nreboot"
        clean_nl = InputValidator.sanitize(dirty_nl)
        self.assertEqual(clean_nl, "127.0.0.1reboot") # Newline silinmeli
        print("[InputValidator] Injection Testi: OK")

    # =========================================================================
    # 2. Secure Cleaner Testleri
    # =========================================================================
    def test_session_expiry(self):
        print("\n[SecureCleaner] Zaman Aşımı Testi...")
        cleaner = get_cleaner()
        exec_mgr = get_execution_manager()
        
        # Gerçek temp path'ini bul
        dummy_path = exec_mgr.get_temp_path("dummy.txt")
        temp_dir = os.path.dirname(dummy_path)
        
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        print(f"   -> Hedef Temp Dizin: {temp_dir}")
        
        # Eski dosya oluştur (sentinel_ prefix ile)
        old_file = os.path.join(temp_dir, "sentinel_old_session.txt")
        with open(old_file, "w") as f: f.write("old data")
        
        # Dosya tarihini 5 gün geriye al
        past = time.time() - (5 * 86400)
        os.utime(old_file, (past, past))
        
        # Yeni dosya oluştur
        new_file = os.path.join(temp_dir, "sentinel_new_session.txt")
        with open(new_file, "w") as f: f.write("new data")
        
        time.sleep(0.1) 
        
        deleted = cleaner.cleanup_old_sessions(days=3)
        
        exists_old = os.path.exists(old_file)
        exists_new = os.path.exists(new_file)
        
        if exists_old:
            cleaner.delete(old_file)
        cleaner.delete(new_file)
        
        self.assertEqual(deleted, 1, "Yanlış sayıda dosya silindi")
        self.assertFalse(exists_old, "Eski dosya silinmedi")
        self.assertTrue(exists_new, "Yeni dosya yanlışlıkla silindi")
        print("[SecureCleaner] Session Temizliği: OK")

    # =========================================================================
    # 3. Execution Manager Testleri
    # =========================================================================
    def test_execution_manager(self):
        print("\n[ExecutionManager] Mantık Testi...")
        mgr = get_execution_manager()
        
        # Dinamik mod tespiti tetiklenmeli
        current_mode = mgr.mode 
        print(f"   -> Algılanan Mod: {current_mode.value}")
        
        tool = "nmap"
        args = ["-F", "localhost"]
        
        cmd, final_args, temp_path = mgr.prepare_command(tool, args)
        
        if current_mode == ExecutionMode.DOCKER:
            self.assertEqual(cmd, "docker")
            self.assertTrue("/app/output/" in temp_path)
        else:
            self.assertEqual(cmd, "nmap")
            
        print("[ExecutionManager] Komut Hazırlama: OK")

if __name__ == '__main__':
    print("SPRINT 3 VALIDATION SUITE (UPDATED)")
    print("=" * 60)
    unittest.main(exit=False)
