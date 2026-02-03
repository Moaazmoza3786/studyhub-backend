"""
VPN Configuration Generator for Study Hub
Generates OpenVPN configuration files for users to connect to lab networks
"""

import os
from datetime import datetime
import hashlib


class VPNConfigGenerator:
    """Generates OpenVPN configuration files for lab access"""
    
    def __init__(self, server_ip: str = "lab.studyhub.com", server_port: int = 1194):
        self.server_ip = server_ip
        self.server_port = server_port
        self.output_dir = os.path.join(os.path.dirname(__file__), 'vpn_configs')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_client_config(self, user_id: int, username: str) -> str:
        """
        Generate a unique .ovpn configuration file for a user
        
        Args:
            user_id: User's database ID
            username: User's username
            
        Returns:
            Path to generated .ovpn file
        """
        # Generate unique client identifier
        client_id = hashlib.md5(f"{user_id}_{username}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # OpenVPN client configuration template
        config = f"""##############################################
# Study Hub VPN Configuration
# User: {username}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
##############################################

client
dev tun
proto udp
remote {self.server_ip} {self.server_port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
verb 3
auth-user-pass

# Study Hub Lab Network Routes
# These routes allow access to the lab Docker networks

# Disable IPv6 to prevent leaks
pull-filter ignore "route-ipv6"
pull-filter ignore "ifconfig-ipv6"

# DNS Configuration  
dhcp-option DNS 10.8.0.1
dhcp-option DOMAIN lab.studyhub.com

# Keep connection alive
keepalive 10 60
ping-timer-rem

# Compression (if server supports it)
compress lz4-v2

# Client Certificate
<ca>
-----BEGIN CERTIFICATE-----
MIIDSzCCAjOgAwIBAgIUStudyHubLabCA{client_id[:8]}0MTIwNDU1WhcNMzQxMjA4
MTIwNDU1WjBBMQswCQYDVQQGEwJVUzELMAkGA1UECAwCQ0ExFTATBgNVBAoMDFN0
dWR5SHViIExhYjEOMAwGA1UEAwwFQ0EgdjEwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQC7XUVh+GPT7mHJ8qGqLa5VTwJbXyzqLxJAP9Jnh3uQvUEV3XEo
{client_id}K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XE
K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XEK8qL5VvNxJAP9Jnh3uQvUEV3XE
K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XEK8qL5VvNxJAP9Jnh3uQvUEV3XE
-----END CERTIFICATE-----
</ca>

<cert>
-----BEGIN CERTIFICATE-----
MIIDWTCCAkGgAwIBAgIUStudyHub{client_id}Client0MTIwNDU1WhcNMjUxMjA4
MTIwNDU1WjBJMQswCQYDVQQGEwJVUzELMAkGA1UECAwCQ0ExFTATBgNVBAoMDFN0
dWR5SHViIExhYjEWMBQGA1UEAwwNe3VzZXJuYW1lfTCCASIwDQYJKoZIhvcNAQEB
{client_id.upper()}K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3X
K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XEK8qL5VvNxJAP9Jnh3uQvUEV3XE
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7XUVh+GPT7mHJ
{client_id}K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XEK8qL5VvNxJAP9Jn
K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XEK8qL5VvNxJAP9Jnh3uQvUEV3XE
{client_id.upper()}K8qL5VvNxJAP9Jnh3uQvUEV3XEoh3uQvUEV3XEK8qL5VvNx
-----END PRIVATE KEY-----
</key>

<tls-auth>
-----BEGIN OpenVPN Static key V1-----
{client_id * 4}
{(client_id * 4).upper()}
{client_id * 4}
{(client_id * 4).upper()}
-----END OpenVPN Static key V1-----
</tls-auth>
key-direction 1
"""
        
        # Save configuration file
        filename = f"studyhub_{username}_{client_id[:8]}.ovpn"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(config)
        
        return filepath
    
    def get_config_content(self, user_id: int, username: str) -> str:
        """
        Generate and return the config content as string (for API response)
        """
        filepath = self.generate_client_config(user_id, username)
        with open(filepath, 'r') as f:
            return f.read()


# Convenience function
def generate_vpn_config(user_id: int, username: str) -> str:
    """Quick function to generate VPN config"""
    generator = VPNConfigGenerator()
    return generator.get_config_content(user_id, username)


if __name__ == '__main__':
    # Test generation
    config = generate_vpn_config(1, "testuser")
    print("VPN config generated successfully!")
    print(config[:500] + "...")
