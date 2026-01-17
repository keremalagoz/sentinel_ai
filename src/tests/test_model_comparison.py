"""
SENTINEL AI - LLM Model Karsilastirma Testi
WhiteRabbitNeo vs Llama 3 performans ve dogruluk testi

Kullanim:
    python src/tests/test_model_comparison.py
"""

import json
import time
import requests
import subprocess
from typing import Optional, Dict, Any, List


def get_gpu_usage() -> Dict[str, Any]:
    """NVIDIA GPU kullanim bilgisini al"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "gpu_util": f"{parts[0]}%",
                "mem_used": f"{parts[1]} MB",
                "mem_total": f"{parts[2]} MB",
                "available": True
            }
    except Exception:
        pass
    return {"available": False}

# Test senaryolari: (kullanici_girdisi, beklenen_tool, beklenen_flagler)
TEST_CASES = [
    # Basit taramalar
    ("192.168.1.0/24 agini tara", "nmap", ["-sn"]),
    ("Hedef: 10.0.0.1 - portlarini tara", "nmap", ["-p"]),
    ("scanme.nmap.org sitesinin acik portlarini bul", "nmap", ["-p"]),
    
    # Web taramalari
    ("example.com sitesinde dizin taramasi yap", "gobuster", ["dir", "-u"]),
    ("Web sunucusundaki zafiyetleri tara", "nikto", ["-h"]),
    
    # DNS ve bilgi toplama
    ("google.com icin DNS sorgusu yap", "nslookup", []),
    ("example.com domaininin whois bilgilerini getir", "whois", []),
    
    # Karmasik senaryolar
    ("192.168.1.1 hedefinde SYN scan yap ve servis versiyonlarini bul", "nmap", ["-sS", "-sV"]),
    ("Hedef sunucuda SSH brute force dene", "hydra", ["ssh"]),
    
    # Edge cases - yanlis flag uretme testi
    ("nmap ile detayli tarama yap", "nmap", []),  # Uydurma flag uretmemeli
    ("hizli bir port taramasi", "nmap", []),  # Gecerli flagler kullanmali
]


# Model -> Endpoint mapping
# Local Ollama for faster development
MODEL_ENDPOINTS = {
    "whiterabbitneo": "http://localhost:11434",  # Local Ollama
    "llama3:8b": "http://localhost:11434",  # Local Ollama
}


def call_ollama(model: str, prompt: str, base_url: str = None) -> Dict[str, Any]:
    """Ollama API'ye istek gonder"""
    
    # Model'e gore endpoint sec
    if base_url is None:
        base_url = MODEL_ENDPOINTS.get(model, "http://localhost:11434")
    
    system_prompt = """Sen SENTINEL AI, bir siber guvenlik test asistanisin.
Kullanicinin talebini JSON formatinda komuta cevir.

YANIT FORMATI:
{
    "command": {
        "tool": "arac_adi",
        "arguments": ["arg1", "arg2"],
        "requires_root": false,
        "risk_level": "low|medium|high",
        "explanation": "aciklama"
    },
    "message": "kullaniciya mesaj",
    "needs_clarification": false
}"""

    try:
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 500
                }
            },
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "response": result.get("response", ""),
                "elapsed_seconds": elapsed,
                "model": model
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "elapsed_seconds": elapsed,
                "model": model
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_seconds": 0,
            "model": model
        }


def extract_json(text: str) -> Optional[Dict]:
    """Text icinden JSON cikar"""
    try:
        # Markdown code block kontrolu
        import re
        pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        match = re.search(pattern, text)
        if match:
            return json.loads(match.group(1))
        
        # Normal JSON arama
        start = text.find('{')
        if start == -1:
            return None
        
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        if end > start:
            return json.loads(text[start:end + 1])
        
        return None
    except json.JSONDecodeError:
        return None


def validate_response(response: Dict, expected_tool: str, expected_flags: List[str]) -> Dict[str, Any]:
    """Yaniti dogrula"""
    
    result = {
        "tool_correct": False,
        "flags_found": [],
        "flags_missing": [],
        "flags_invalid": [],
        "has_hallucination": False
    }
    
    if not response.get("success"):
        return result
    
    parsed = extract_json(response.get("response", ""))
    if not parsed:
        return result
    
    command = parsed.get("command", {})
    if not command:
        return result
    
    # Tool kontrolu
    tool = command.get("tool", "")
    result["tool_correct"] = tool.lower() == expected_tool.lower()
    
    # Flag kontrolu
    arguments = command.get("arguments", [])
    args_str = " ".join(arguments) if isinstance(arguments, list) else str(arguments)
    
    for flag in expected_flags:
        if flag in args_str:
            result["flags_found"].append(flag)
        else:
            result["flags_missing"].append(flag)
    
    # Hallucination kontrolu - gecersiz flag tespiti
    # Nmap icin bilinen gecerli flagler
    VALID_NMAP_FLAGS = [
        "-sn", "-sS", "-sT", "-sU", "-sV", "-sC", "-O", "-A",
        "-p", "-p-", "-F", "-T0", "-T1", "-T2", "-T3", "-T4", "-T5",
        "-Pn", "-n", "-R", "-v", "-vv", "-d", "-oN", "-oX", "-oG",
        "--open", "--top-ports", "--script", "--version-intensity"
    ]
    
    if tool.lower() == "nmap":
        for arg in arguments:
            if arg.startswith("-") and not any(arg.startswith(v) for v in VALID_NMAP_FLAGS):
                # Bilinmeyen flag - potansiyel hallucination
                if not arg.startswith("-p") and not arg[1:].isdigit():  # Port numarasi degilse
                    result["flags_invalid"].append(arg)
                    result["has_hallucination"] = True
    
    return result


def run_comparison(models: List[str]):
    """Modelleri karsilastir"""
    
    print("=" * 70)
    print("SENTINEL AI - LLM Model Karsilastirma Testi")
    print("=" * 70)
    
    # GPU durumunu kontrol et
    gpu_info = get_gpu_usage()
    if gpu_info["available"]:
        print(f"\nGPU: Mevcut ({gpu_info['mem_used']}/{gpu_info['mem_total']})")
    else:
        print("\nGPU: Kullanilmiyor (CPU modu)")
    
    results = {model: {"correct": 0, "total": 0, "hallucinations": 0, "avg_time": 0, "gpu_peak": "0%"} for model in models}
    
    for i, (prompt, expected_tool, expected_flags) in enumerate(TEST_CASES):
        print(f"\n[Test {i+1}/{len(TEST_CASES)}] {prompt[:50]}...")
        
        for model in models:
            print(f"  [{model}] ", end="", flush=True)
            
            # GPU oncesi
            gpu_before = get_gpu_usage()
            
            response = call_ollama(model, prompt)
            
            # GPU sonrasi
            gpu_after = get_gpu_usage()
            
            validation = validate_response(response, expected_tool, expected_flags)
            
            results[model]["total"] += 1
            
            if response.get("success"):
                results[model]["avg_time"] += response["elapsed_seconds"]
                
                # GPU kullanimi
                gpu_str = ""
                if gpu_after["available"]:
                    gpu_str = f" GPU:{gpu_after['gpu_util']}"
                    # Peak'i kaydet
                    current_peak = int(results[model]["gpu_peak"].replace("%", ""))
                    new_util = int(gpu_after["gpu_util"].replace("%", ""))
                    if new_util > current_peak:
                        results[model]["gpu_peak"] = gpu_after["gpu_util"]
                
                if validation["tool_correct"]:
                    results[model]["correct"] += 1
                    status = "[OK]"
                else:
                    status = "[WRONG TOOL]"
                
                if validation["has_hallucination"]:
                    results[model]["hallucinations"] += 1
                    status += " [HALLUCINATION: " + ", ".join(validation["flags_invalid"]) + "]"
                
                print(f"{status} ({response['elapsed_seconds']:.1f}s){gpu_str}")
            else:
                print(f"[ERROR] {response.get('error', 'Unknown')}")
    
    # Ozet
    print("\n" + "=" * 70)
    print("SONUCLAR")
    print("=" * 70)
    
    for model in models:
        r = results[model]
        if r["total"] > 0:
            accuracy = (r["correct"] / r["total"]) * 100
            avg_time = r["avg_time"] / r["total"]
            print(f"\n{model}:")
            print(f"  Dogruluk: {r['correct']}/{r['total']} ({accuracy:.1f}%)")
            print(f"  Hallucination: {r['hallucinations']}")
            print(f"  Ortalama Yanit Suresi: {avg_time:.1f}s")
            print(f"  GPU Peak Kullanim: {r['gpu_peak']}")
    
    # Kazanan
    print("\n" + "-" * 70)
    best_model = max(models, key=lambda m: (results[m]["correct"], -results[m]["avg_time"]))
    print(f"TAVSIYE: {best_model.upper()}")
    print("-" * 70)
    
    return results


def check_model_available(model: str, endpoint: str) -> bool:
    """Model mevcut mu kontrol et"""
    try:
        response = requests.get(f"{endpoint}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(m.get("name", "").startswith(model) for m in models)
        return False
    except:
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("SENTINEL AI - LLM Model Karsilastirma Testi")
    print("WhiteRabbitNeo vs Llama 3 (Local Ollama)")
    print("=" * 70)
    
    # Test edilecek modeller ve endpoint'leri
    test_models = [
        ("whiterabbitneo", "http://localhost:11434", "Local Ollama"),
        ("llama3:8b", "http://localhost:11434", "Local Ollama"),
    ]
    
    available_models = []
    
    print("\nModel durumu kontrol ediliyor...")
    for model, endpoint, desc in test_models:
        if check_model_available(model, endpoint):
            available_models.append(model)
            print(f"  [OK] {model} ({desc})")
        else:
            print(f"  [--] {model} ({desc}) - MEVCUT DEGIL")
    
    if not available_models:
        print("\nHicbir model bulunamadi!")
        print("WhiteRabbitNeo icin: ollama pull whiterabbitneo")
        print("Llama 3 icin: docker compose up -d llama-service")
        exit(1)
    
    print(f"\nTest edilecek modeller: {available_models}")
    print("Baslatiliyor...\n")
    
    run_comparison(available_models)
