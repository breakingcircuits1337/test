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