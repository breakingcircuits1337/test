import json

def ping(ip: str, count: int = 1, packet_size: int = 56, timeout: int = 1) -> str:
    try:
        from network_diagnostic_skills import NetworkDiagnosticSkill
    except ImportError:
        raise ImportError("network_diagnostic_skills.py (and dependencies) are required.")
    skill = NetworkDiagnosticSkill()
    return skill.ping(ip, packet_size=packet_size, count=count, timeout=timeout)

def traceroute(ip: str, max_hops: int = 30, packet_size: int = 40) -> str:
    try:
        from network_diagnostic_skills import NetworkDiagnosticSkill
    except ImportError:
        raise ImportError("network_diagnostic_skills.py (and dependencies) are required.")
    skill = NetworkDiagnosticSkill()
    return skill.traceroute(ip, max_hops=max_hops, packet_size=packet_size)

def dns_lookup(domain: str, record_type: str = "A", dns_server: str = "8.8.8.8") -> str:
    try:
        from network_diagnostic_skills import DNSLookupSkill
    except ImportError:
        raise ImportError("network_diagnostic_skills.py (and dependencies) are required.")
    skill = DNSLookupSkill()
    return skill.lookup(domain, record_type, dns_server)

def port_scan(ip: str, start_port: int = 1, end_port: int = 1024) -> str:
    try:
        from network_diagnostic_skills import PortScannerSkill
    except ImportError:
        raise ImportError("network_diagnostic_skills.py (and dependencies) are required.")
    skill = PortScannerSkill()
    return skill.scan(ip, start_port, end_port)

def interface_info() -> str:
    try:
        from network_diagnostic_skills import NetworkInterfaceSkill
    except ImportError:
        raise ImportError("network_diagnostic_skills.py (and dependencies) are required.")
    skill = NetworkInterfaceSkill()
    info = skill.get_info()
    # If already str, return as is; else pretty-print JSON
    if isinstance(info, str):
        return info
    try:
        return json.dumps(info, indent=2)
    except Exception:
        return str(info)

def tcp_test(host: str, port: int, timeout: int = 5) -> str:
    try:
        from network_diagnostic_skills import TCPConnectionTestSkill
    except ImportError:
        raise ImportError("network_diagnostic_skills.py (and dependencies) are required.")
    skill = TCPConnectionTestSkill()
    return skill.test(host, port, timeout)