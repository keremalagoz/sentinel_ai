"""Entity ID Generator - Canonical ID Strategy

Sprint 1 Week 1 Implementation
Locked Design: docs/entity_id_strategy.md

Merkezi, deterministic entity ID generation.
Parser'lar bu class'ı kullanır, override yasak.
"""

import hashlib
from typing import Optional


class EntityIDGenerator:
    """
    Merkezi entity ID üretimi.
    
    Tüm parser'lar bu class'ı kullanır.
    ID formatları canonical ve deterministik.
    
    Design: docs/entity_id_strategy.md
    """
    
    @staticmethod
    def host_id(ip: str) -> str:
        """
        Generate canonical host ID from IP address.
        
        Args:
            ip: IP address (IPv4 or IPv6)
            
        Returns:
            Canonical host ID
            
        Examples:
            192.168.1.10 -> host_192_168_1_10
            ::1 -> host_0_0_0_0_0_0_0_1
        """
        # Normalize: Replace dots and colons with underscores
        normalized = ip.replace('.', '_').replace(':', '_')
        return f"host_{normalized}"
    
    @staticmethod
    def port_id(ip: str, port: int, protocol: str) -> str:
        """
        Generate canonical port ID.
        
        Args:
            ip: Host IP address
            port: Port number
            protocol: Protocol (tcp, udp)
            
        Returns:
            Canonical port ID
            
        Examples:
            192.168.1.10:80/tcp -> host_192_168_1_10_port_80_tcp
            192.168.1.10:53/udp -> host_192_168_1_10_port_53_udp
        """
        host_id = EntityIDGenerator.host_id(ip)
        proto = protocol.lower()
        return f"{host_id}_port_{port}_{proto}"
    
    @staticmethod
    def service_id(port_id: str, service_name: str) -> str:
        """
        Generate canonical service ID.
        
        Args:
            port_id: Port ID (from port_id())
            service_name: Service name
            
        Returns:
            Canonical service ID
            
        Examples:
            host_192_168_1_10_port_80_tcp + http 
            -> host_192_168_1_10_port_80_tcp_service_http
        """
        # Normalize: Lowercase, replace spaces with underscores
        normalized_name = service_name.lower().replace(' ', '_')
        return f"{port_id}_service_{normalized_name}"
    
    @staticmethod
    def vuln_id(service_id: str, cve_or_type: str) -> str:
        """
        Generate canonical vulnerability ID.
        
        Args:
            service_id: Service ID (from service_id())
            cve_or_type: CVE ID or vulnerability type
            
        Returns:
            Canonical vulnerability ID
            
        Examples:
            service_id + CVE-2024-1234 
            -> ...service_http_vuln_cve_2024_1234
            
            service_id + weak_cipher 
            -> ...service_ssh_vuln_weak_cipher
        """
        # Normalize: Lowercase, replace hyphens with underscores
        normalized = cve_or_type.lower().replace('-', '_')
        return f"{service_id}_vuln_{normalized}"
    
    @staticmethod
    def web_resource_id(service_id: str, url: str) -> str:
        """
        Generate canonical web resource ID.
        
        Args:
            service_id: Service ID (from service_id())
            url: Full URL path
            
        Returns:
            Canonical web resource ID (with path hash)
            
        Examples:
            service_id + http://192.168.1.10/admin 
            -> ...service_http_web_hash_abc12345
            
        Note: Hash used to handle long/special-char URLs
        """
        # Normalize: Lowercase, strip trailing slash
        normalized_url = url.lower().rstrip('/')
        
        # Hash to fixed length (8 chars)
        hash_value = hashlib.md5(normalized_url.encode()).hexdigest()[:8]
        
        return f"{service_id}_web_hash_{hash_value}"
    
    @staticmethod
    def dns_id(domain: str) -> str:
        """
        Generate canonical DNS ID.
        
        Args:
            domain: Domain name
            
        Returns:
            Canonical DNS ID
            
        Examples:
            example.com -> dns_example_com
            sub.example.com -> dns_sub_example_com
        """
        # Normalize: Lowercase, replace dots with underscores
        normalized = domain.lower().replace('.', '_')
        return f"dns_{normalized}"
    
    @staticmethod
    def cert_id(fingerprint: str) -> str:
        """
        Generate canonical certificate ID.
        
        Args:
            fingerprint: Certificate SHA256 fingerprint
            
        Returns:
            Canonical certificate ID
            
        Examples:
            AB:CD:EF:12:34... -> cert_abcdef1234...
        """
        # Normalize: Lowercase, remove colons
        normalized = fingerprint.lower().replace(':', '')
        return f"cert_{normalized}"
    
    @staticmethod
    def credential_id(username: str, service_id: str) -> str:
        """
        Generate canonical credential ID.
        
        Args:
            username: Username
            service_id: Service ID (from service_id())
            
        Returns:
            Canonical credential ID
            
        Examples:
            admin @ service_id 
            -> cred_admin_host_192_168_1_10_port_22_tcp_service_ssh
            
        Note: Password NEVER in ID (stored encrypted in entity data)
        """
        # Normalize: Lowercase
        normalized_user = username.lower()
        return f"cred_{normalized_user}_{service_id}"
    
    @staticmethod
    def file_id(host_id: str, file_path: str) -> str:
        """
        Generate canonical file ID.
        
        Args:
            host_id: Host ID (from host_id())
            file_path: Absolute file path
            
        Returns:
            Canonical file ID (with path hash)
            
        Examples:
            host_id + /etc/passwd 
            -> file_host_192_168_1_10_hash_abc12345
            
        Note: Hash used to handle long paths
        """
        # Hash path to fixed length (8 chars)
        hash_value = hashlib.md5(file_path.encode()).hexdigest()[:8]
        
        return f"file_{host_id}_hash_{hash_value}"


class IDValidator:
    """
    Validate entity ID formats.
    
    Used in tests to ensure parser compliance.
    """
    
    import re
    
    # ID format patterns
    HOST_PATTERN = re.compile(r'^host_[\d_]+$')
    PORT_PATTERN = re.compile(r'^host_[\d_]+_port_\d+_(tcp|udp)$')
    SERVICE_PATTERN = re.compile(r'^host_[\d_]+_port_\d+_(tcp|udp)_service_[a-z_]+$')
    VULN_PATTERN = re.compile(r'^host_[\d_]+_port_\d+_(tcp|udp)_service_[a-z_]+_vuln_[a-z_0-9]+$')
    WEB_PATTERN = re.compile(r'^host_[\d_]+_port_\d+_(tcp|udp)_service_[a-z_]+_web_hash_[a-f0-9]{8}$')
    DNS_PATTERN = re.compile(r'^dns_[a-z_0-9]+$')
    CERT_PATTERN = re.compile(r'^cert_[a-f0-9]+$')
    CRED_PATTERN = re.compile(r'^cred_[a-z_0-9]+_host_[\d_]+_port_\d+_(tcp|udp)_service_[a-z_]+$')
    FILE_PATTERN = re.compile(r'^file_host_[\d_]+_hash_[a-f0-9]{8}$')
    
    @classmethod
    def validate_host_id(cls, entity_id: str) -> bool:
        """Validate host ID format"""
        return bool(cls.HOST_PATTERN.match(entity_id))
    
    @classmethod
    def validate_port_id(cls, entity_id: str) -> bool:
        """Validate port ID format"""
        return bool(cls.PORT_PATTERN.match(entity_id))
    
    @classmethod
    def validate_service_id(cls, entity_id: str) -> bool:
        """Validate service ID format"""
        return bool(cls.SERVICE_PATTERN.match(entity_id))
    
    @classmethod
    def validate_vuln_id(cls, entity_id: str) -> bool:
        """Validate vulnerability ID format"""
        return bool(cls.VULN_PATTERN.match(entity_id))
    
    @classmethod
    def validate_web_resource_id(cls, entity_id: str) -> bool:
        """Validate web resource ID format"""
        return bool(cls.WEB_PATTERN.match(entity_id))
    
    @classmethod
    def validate_dns_id(cls, entity_id: str) -> bool:
        """Validate DNS ID format"""
        return bool(cls.DNS_PATTERN.match(entity_id))
    
    @classmethod
    def validate_cert_id(cls, entity_id: str) -> bool:
        """Validate certificate ID format"""
        return bool(cls.CERT_PATTERN.match(entity_id))
    
    @classmethod
    def validate_cred_id(cls, entity_id: str) -> bool:
        """Validate credential ID format"""
        return bool(cls.CRED_PATTERN.match(entity_id))
    
    @classmethod
    def validate_file_id(cls, entity_id: str) -> bool:
        """Validate file ID format"""
        return bool(cls.FILE_PATTERN.match(entity_id))


# Example usage
if __name__ == "__main__":
    gen = EntityIDGenerator()
    
    # Host
    host_id = gen.host_id("192.168.1.10")
    print(f"Host ID: {host_id}")
    print(f"Valid: {IDValidator.validate_host_id(host_id)}")
    
    # Port
    port_id = gen.port_id("192.168.1.10", 80, "tcp")
    print(f"\nPort ID: {port_id}")
    print(f"Valid: {IDValidator.validate_port_id(port_id)}")
    
    # Service
    service_id = gen.service_id(port_id, "http")
    print(f"\nService ID: {service_id}")
    print(f"Valid: {IDValidator.validate_service_id(service_id)}")
    
    # Vulnerability
    vuln_id = gen.vuln_id(service_id, "CVE-2024-1234")
    print(f"\nVuln ID: {vuln_id}")
    print(f"Valid: {IDValidator.validate_vuln_id(vuln_id)}")
    
    # Web resource
    web_id = gen.web_resource_id(service_id, "http://192.168.1.10/admin")
    print(f"\nWeb ID: {web_id}")
    print(f"Valid: {IDValidator.validate_web_resource_id(web_id)}")
    
    # DNS
    dns_id = gen.dns_id("example.com")
    print(f"\nDNS ID: {dns_id}")
    print(f"Valid: {IDValidator.validate_dns_id(dns_id)}")
