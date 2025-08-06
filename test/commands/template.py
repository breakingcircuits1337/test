import typer

@app.command()
def ip_port_scan(target: str = typer.Argument(..., help="Target IP/CIDR or comma-separated list"),
                 port_mode: str = typer.Option("Common Ports", "--mode", help="Port scan mode: Common Ports, All Ports (1-65535), Custom Range, Custom List"),
                 custom_ports: str = typer.Option("", "--custom", help="Custom port range or list when mode is Custom Range/List"),
                 threads: int = typer.Option(50, "--threads", help="Number of concurrent threads (1-500)"),
                 timeout: float = typer.Option(0.5, "--timeout", help="Timeout seconds per connection (0.1-10)"),
                 no_discover: bool = typer.Option(False, "--no-discover", help="Skip ARP host discovery")):
    """Run the LAN IP & port scanner from ipport.py head-less and print the results."""
    from modules import ipport_wrapper
    result = ipport_wrapper.scan(target, port_mode, custom_ports, threads, timeout, no_discover)
    typer.echo(result)
    return result

@app.command()
def network_ping(ip: str = typer.Argument(..., help="Target IP to ping"),
                 count: int = typer.Option(1, "--count", help="Number of packets"),
                 packet_size: int = typer.Option(56, "--size", help="Packet size"),
                 timeout: int = typer.Option(1, "--timeout", help="Timeout per packet (seconds)")):
    """Ping a host."""
    from modules import network_skills_wrapper
    result = network_skills_wrapper.ping(ip, count, packet_size, timeout)
    typer.echo(result)
    return result

@app.command()
def network_traceroute(ip: str = typer.Argument(..., help="Target IP for traceroute"),
                       max_hops: int = typer.Option(30, "--max-hops", help="Max hops"),
                       packet_size: int = typer.Option(40, "--size", help="Packet size")):
    """Traceroute to a host."""
    from modules import network_skills_wrapper
    result = network_skills_wrapper.traceroute(ip, max_hops, packet_size)
    typer.echo(result)
    return result

@app.command()
def network_dns_lookup(domain: str = typer.Argument(..., help="Domain to query"),
                       record_type: str = typer.Option("A", "--type", help="DNS record type"),
                       dns_server: str = typer.Option("8.8.8.8", "--server", help="DNS server")):
    """DNS lookup."""
    from modules import network_skills_wrapper
    result = network_skills_wrapper.dns_lookup(domain, record_type, dns_server)
    typer.echo(result)
    return result

@app.command()
def network_port_scan(ip: str = typer.Argument(..., help="Target IP for port scan"),
                      start_port: int = typer.Option(1, "--start", help="Start port"),
                      end_port: int = typer.Option(1024, "--end", help="End port")):
    """Port scan using TCP SYN."""
    from modules import network_skills_wrapper
    result = network_skills_wrapper.port_scan(ip, start_port, end_port)
    typer.echo(result)
    return result

@app.command()
def network_interface_info():
    """Show interface info (JSON)."""
    from modules import network_skills_wrapper
    result = network_skills_wrapper.interface_info()
    typer.echo(result)
    return result

@app.command()
def network_tcp_test(host: str = typer.Argument(..., help="Host for TCP test"),
                     port: int = typer.Argument(..., help="Port"),
                     timeout: int = typer.Option(5, "--timeout", help="Timeout (seconds)")):
    """Test TCP connection to host:port."""
    from modules import network_skills_wrapper
    result = network_skills_wrapper.tcp_test(host, port, timeout)
    typer.echo(result)
    return result