"""
Interaktif prompt test scripti.
Ghost Panel'i test etmek için kullanilir.
"""
import sys
import time

print("=== SENTINEL Interactive Test ===")
print()
time.sleep(0.5)

print("Bu script interaktif girdi bekleyecek.")
print()
time.sleep(0.5)

response = input("Devam etmek istiyor musunuz? [y/n]: ")
print(f"Cevabiniz: {response}")
print()

if response.lower() in ('y', 'yes', 'e', 'evet'):
    print("Tamam, devam ediliyor...")
    time.sleep(0.5)
    
    password = input("Parola girin (password): ")
    print(f"Girilen parola: {'*' * len(password)}")
    print()
    
    confirm = input("Onayliyor musunuz? (Y/N): ")
    print(f"Onay: {confirm}")
else:
    print("Iptal edildi.")

print()
print("=== Test Tamamlandi ===")

