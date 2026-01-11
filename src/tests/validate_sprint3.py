
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
        # Test için geçici klasörler
        os.makedirs("temp/test_sessions", exist_ok=True)
        os.makedirs("temp/sentinel_safe", exist_ok=True)
    
    def tearDown(self):
        # Temizlik
        pass # Cleaner testlerinde manuel temizleyeceğiz

    # =========================================================================
    # 1. Input Validator Testleri
    # =========================================================================
    def test_validator_ip(self):
        print("\n[InputValidator] IP Testi...")
        self.assertTrue(InputValidator.validate_ip("192.168.1.1"))
        self.assertTrue(InputValidator.validate_ip("10.0.0.1/24")) # CIDR
        self.assertFalse(InputValidator.validate_ip("999.999.999.999"))
        self.assertFalse(InputValidator.validate_ip("abc.def.ghi.jkl"))
        print("[OK] IP Validasyonu Basarili")

    def test_validator_injection(self):
        print("\n[InputValidator] Injection Testi...")
        dirty = "127.0.0.1; rm -rf /"
        clean = InputValidator.sanitize(dirty)
        self.assertEqual(clean, "127.0.0.1 rm -rf /") # Noktalı virgül gitmeli
        
        args = ["-sS", ";ls", "&cat"]
        safe_args = [arg for arg in args if InputValidator.is_safe_arg(arg)]
        self.assertEqual(safe_args, ["-sS"]) # Diğerleri elenmeli
        print("[OK] Injection Korumasi Basarili")

    # =========================================================================
    # 2. Secure Cleaner Testleri (EN KRİTİK)
    # =========================================================================
    def test_cleaner_whitelist(self):
        print("\n[SecureCleaner] Whitelist Testi...")
        cleaner = get_cleaner()
        
        # 1. Güvenli Dosya (Temp içinde)
        safe_file = "temp/session_test_safe.txt"
        with open(safe_file, "w") as f: f.write("test data")
        
        # Silmeye çalış
        result = cleaner.delete(safe_file)
        self.assertTrue(result, "Güvenli dosya silinemedi!")
        self.assertFalse(os.path.exists(safe_file), "Dosya hala diskte!")
        
        # 2. Güvensiz Dosya (Proje root'unda)
        unsafe_file = "critical_config.txt" 
        with open(unsafe_file, "w") as f: f.write("DONT DELETE ME")
        
        try:
            # Silmeye çalış (Reddedilmeli)
            result = cleaner.delete(unsafe_file)
            self.assertFalse(result, "GÜVENLİK AÇIĞI: Whitelist dışı dosya silindi!")
            self.assertTrue(os.path.exists(unsafe_file), "Kritik dosya silindi!")
        finally:
            os.remove(unsafe_file) # Test bitince biz silelim
            
        print("[OK] Whitelist Korumasi Basarili")

    def test_cleaner_path_traversal(self):
        print("\n[SecureCleaner] Path Traversal Testi...")
        cleaner = get_cleaner()
        
        # ../ denemesi
        traversal_path = "temp/../requirements.txt"
        result = cleaner.delete(traversal_path)
        self.assertFalse(result, "GÜVENLİK AÇIĞI: Path traversal engellenmedi!")
        print("[OK] Path Traversal Korumasi Basarili")

    def test_session_expiry(self):
        print("\n[SecureCleaner] Zaman Aşımı Testi...")
        cleaner = get_cleaner()
        
        # Eski dosya oluştur
        old_file = "temp/session_old.txt"
        with open(old_file, "w") as f: f.write("old data")
        
        # Dosya tarihini 5 gün geriye al
        past = time.time() - (5 * 86400)
        os.utime(old_file, (past, past))
        
        # Yeni dosya oluştur
        new_file = "temp/session_new.txt"
        with open(new_file, "w") as f: f.write("new data")
        
        # Temizlik yap (3 günden eskileri sil)
        # Windows hassasiyetini aşmak için kısa bir sleep
        time.sleep(0.1)
        
        deleted = cleaner.cleanup_old_sessions(days=3)
        
        # Debug bilgisi
        if os.path.exists(old_file):
            print(f"   DEBUG: Eski dosya silinemedi. Mtime: {os.path.getmtime(old_file)}")
        
        self.assertEqual(deleted, 1, "Yanlış sayıda dosya silindi")
        self.assertFalse(os.path.exists(old_file), "Eski dosya silinmedi")
        self.assertTrue(os.path.exists(new_file), "Yeni dosya yanlışlıkla silindi")
        
        # Temizlik
        cleaner.delete(new_file)
        print("[OK] Session Temizligi Basarili")

    # =========================================================================
    # 3. Execution Manager Testleri
    # =========================================================================
    def test_execution_manager(self):
        print("\n[ExecutionManager] Mantık Testi...")
        mgr = get_execution_manager()
        
        print(f"   -> Algılanan Mod: {mgr.mode.value}")
        print(f"   -> OS: {mgr._platform}")
        
        # Komut Hazırlama Testi
        tool = "nmap"
        args = ["-F", "localhost"]
        
        cmd, final_args, temp_path = mgr.prepare_command(tool, args)
        
        if mgr.mode == ExecutionMode.DOCKER:
            self.assertEqual(cmd, "docker")
            self.assertTrue("exec" in final_args)
            self.assertTrue("/app/output/" in temp_path)
            print("[OK] Docker Komut Hazirlama Basarili")
        else:
            self.assertEqual(cmd, "nmap")
            self.assertTrue("exec" not in final_args)
            if mgr.is_linux:
                self.assertTrue("/tmp/" in temp_path)
            print("[OK] Native Komut Hazirlama Basarili")

if __name__ == '__main__':
    print("=== SPRINT 3 VALIDATION SUITE ===")
    print("=" * 60)
    unittest.main(exit=False)
