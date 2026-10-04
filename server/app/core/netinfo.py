import socket


def get_lan_ipv4_addresses() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass
    return ips


def get_primary_ipv4() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        addresses = get_lan_ipv4_addresses()
        return addresses[0] if addresses else "127.0.0.1"
    finally:
        probe.close()


def server_url_for_clients(port: int) -> str:
    return f"http://{get_primary_ipv4()}:{port}"
