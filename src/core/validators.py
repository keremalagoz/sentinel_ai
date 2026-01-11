
import re
import ipaddress
from urllib.parse import urlparse
from typing import Optional, List

class InputValidator:
    """
    Kullanıcı girdilerini doğrulayan güvenlik modülü.
    
    Kapsam:
    - IP Adresi doğrulama
    - Hostname/URL doğrulama
    - Shell Injection karakterleri temizleme
    """
    
    # Yasaklı karakterler (Shell Injection riski taşıyanlar)
    # Not: | ve > bazen pipe için gerekebilir ama kullanıcı girdisinde risklidir.
    # \n, \r, \x00 eklendi - newline/null byte injection önlemi
    DANGEROUS_CHARS = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\\", "'", "\"", "\n", "\r", "\x00"]
    
    # İzin verilen güvenli argüman karakterleri (Alfanümerik + yaygın semboller)
    # Regex: Sadece harf, sayı, tire, nokta, alt çizgi, slash, iki nokta
    SAFE_ARG_PATTERN = re.compile(r'^[a-zA-Z0-9\-._/:]+$')

    @staticmethod
    def validate_ip(ip: str) -> bool:
        """IPv4 veya IPv6 adresi geçerli mi?"""
        try:
            # CIDR desteği için (örn: 192.168.1.0/24)
            if "/" in ip:
                ipaddress.ip_network(ip, strict=False)
            else:
                ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_hostname(hostname: str) -> bool:
        """Domain veya Hostname geçerli mi?"""
        if len(hostname) > 255:
            return False
            
        # URL ise hostname'i ayıkla
        if "://" in hostname:
            try:
                hostname = urlparse(hostname).hostname
                if not hostname: return False
            except Exception:
                return False
                
        # Regex ile domain kontrolü
        # (Basit versiyon: harf/sayı + nokta + tire)
        pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$')
        
        # Localhost istisnası
        if hostname == "localhost":
            return True
            
        # IP adresi ise
        if InputValidator.validate_ip(hostname):
            return True
            
        return bool(pattern.match(hostname))

    @staticmethod
    def sanitize(text: str) -> str:
        """Tehlikeli karakterleri temizler."""
        if not text:
            return ""
            
        clean_text = text
        for char in InputValidator.DANGEROUS_CHARS:
            clean_text = clean_text.replace(char, "")
            
        return clean_text

    @staticmethod
    def is_safe_arg(arg: str) -> bool:
        """
        Bir komut argümanı tamamen güvenli karakterlerden mi oluşuyor?
        """
        return bool(InputValidator.SAFE_ARG_PATTERN.match(arg))

    @staticmethod
    def validate_target(target: str) -> bool:
        """Genel hedef doğrulaması (IP veya Hostname)"""
        if not target: return False
        
        # Önce sanitizasyon yap, sonra kontrol et
        clean_target = InputValidator.sanitize(target)
        
        return (InputValidator.validate_ip(clean_target) or 
                InputValidator.validate_hostname(clean_target))
