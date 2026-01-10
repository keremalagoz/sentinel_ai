
import sys
import os
import time

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.getcwd())

from src.ai.orchestrator import get_orchestrator

def run_benchmark():
    print("🚀 SENTINEL AI - GPU Hız Testi Başlatılıyor...")
    print("=" * 60)
    
    orch = get_orchestrator()
    local, cloud = orch.check_services()
    if not local:
        print("❌ HATA: Local AI servisine bağlanılamadı!")
        return

    # Sadece hız odaklı tek bir test yapalım (Model belleğe yüklensin)
    prompt = "localhost üzerindeki açık portları bul"
    
    print(f"Isınma turu (Model Loading)...", end=" ", flush=True)
    start = time.time()
    orch.process(prompt, "localhost")
    print(f"Tamam ({time.time() - start:.2f}s)")
    
    print(f"\n⚡ HIZ TESTİ: '{prompt}'", end=" ", flush=True)
    start = time.time()
    response = orch.process(prompt, "localhost")
    duration = time.time() - start
    
    print(f"\n⏱️  Süre: {duration:.2f} saniye")
    print("=" * 60)
    
    if duration < 10:
        print("✅ GPU AKTİF GÖRÜNÜYOR! (Çok Hızlı)")
    else:
        print("⚠️  HALA YAVAŞ (Muhtemelen CPU)")
        
if __name__ == "__main__":
    run_benchmark()
