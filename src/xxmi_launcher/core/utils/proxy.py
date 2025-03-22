from enum import Enum
from dataclasses import dataclass, field


class ProxyType(Enum):
    HTTPS = 'HTTPS'
    SOCKS5 = 'SOCKS5'


@dataclass
class ProxyConfig:
    enable: bool = False
    type: str = ProxyType.HTTPS.value
    host: str = ''
    port: str = ''
    use_credentials: bool = False
    user: str = ''
    password: str = ''
    proxy_dns_via_socks5: bool = True

    def verify(self):
        if not self.host:
            raise ValueError('Proxy host is not specified!')
        if not self.port:
            raise ValueError('Proxy port is not specified!')
        if not self.port.isnumeric():
            raise ValueError('Proxy port must be numeric value!')


class ProxyManager:
    def __init__(self):
        self.proxies = {}

    def configure(self, cfg: ProxyConfig):
        self.proxies = {}

        if not cfg.enable:
            return

        cfg.verify()

        try:
            proxy_type = ProxyType(cfg.type)
        except Exception as e:
            proxy_type = ProxyType.HTTPS

        host, port = cfg.host.strip(), cfg.port.strip()

        user, password = None, None
        
        if cfg.use_credentials:
            user = cfg.user.strip()
            password = cfg.password.strip()

        if proxy_type == ProxyType.SOCKS5:
            if cfg.proxy_dns_via_socks5:
                scheme = 'socks5h'
            else:
                scheme = 'socks5'
        else:
            scheme = 'http'

        self.add_proxy('https', scheme, host, port, user, password)

    def add_proxy(self, protocol, scheme, host, port, user = None, password = None):
        if user is None or (not user and not password):
            self.proxies[protocol] = f'{scheme}://{host}:{port}'
        else:
            self.proxies[protocol] = f'{scheme}://{user}:{password}@{host}:{port}'
