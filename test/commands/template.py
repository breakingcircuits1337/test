import typer
import sys

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
def chat():
    """Start a natural language text+voice chat with Ada."""
    from modules.base_assistant import PlainAssistant
    from modules.utils import create_session_logger_id, setup_logging

    session_id = create_session_logger_id()
    logger = setup_logging(session_id)
    logger.info(f"Starting interactive chat session {session_id}")
    assistant = PlainAssistant(logger, session_id)

    print("Type your message (or 'exit' to quit):")
    while True:
        try:
            text = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break
        if text.lower() in {"exit", "quit"}:
            print("Exiting chat.")
            break
        if not text:
            continue
        resp = assistant.process_text(text)
        print(f"Ada: {resp}")

@app.command()
def voice_chat():
    """Start voice conversation with Ada (uses STT)."""
    import subprocess, sys
    subprocess.run([sys.executable, "main_base_assistant.py", "chat"])

@app.command()
def nmap_scan(target: str = typer.Argument(..., help="Target IP or domain"),
              flags: str = typer.Option("-sV -T4", "--flags", help="nmap flags")):
    """Run nmap scan with flags."""
    from modules import security_tools
    typer.echo(security_tools.nmap_scan(target, flags))

@app.command()
def nikto_scan(url: str = typer.Argument(..., help="Target URL"),
               options: str = typer.Option("", "--options", help="Nikto options")):
    """Run nikto web vulnerability scan."""
    from modules import security_tools
    typer.echo(security_tools.nikto_scan(url, options))

@app.command()
def wapiti_scan(url: str = typer.Argument(..., help="Target URL"),
                scope: str = typer.Option("folder", "--scope", help="Wapiti scope")):
    """Run wapiti web scanner."""
    from modules import security_tools
    typer.echo(security_tools.wapiti_scan(url, scope))

@app.command()
def shodan_lookup(query: str = typer.Argument(..., help="Shodan search query")):
    """Query Shodan for internet-facing hosts."""
    from modules import security_tools
    typer.echo(security_tools.shodan_lookup(query))

@app.command()
def censys_lookup(ip: str = typer.Argument(..., help="IP address")):
    """Lookup host info via Censys."""
    from modules import security_tools
    typer.echo(security_tools.censys_lookup(ip))

@app.command()
def exploit_search(keyword: str = typer.Argument(..., help="Keyword or CVE to search exploits for")):
    """Search Exploit-DB or local searchsploit for exploits."""
    from modules import security_tools
    typer.echo(security_tools.exploit_search(keyword))

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

@app.command()
def launch_webui(ip: str = typer.Option("127.0.0.1", "--ip"),
                 port: int = typer.Option(7788, "--port"),
                 theme: str = typer.Option("Ocean", "--theme")):
    """Start the Gradio Web UI."""
    from modules import webui_launcher
    typer.echo(webui_launcher.launch(ip, port, theme))