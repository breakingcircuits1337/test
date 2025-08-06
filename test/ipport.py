import gradio as gr
import socket
import threading
from queue import Queue, Empty as QueueEmpty
import ipaddress
import time
import os

# Scapy import
SCAPY_AVAILABLE = False
try:
    from scapy.all import ARP, Ether, srp
    SCAPY_AVAILABLE = True
except ImportError:
    pass # Will notify user in GUI if needed

COMMON_PORTS = {
    20: 'FTP-Data', 21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP',
    53: 'DNS', 67: 'DHCP Server', 68: 'DHCP Client', 69: 'TFTP', 80: 'HTTP',
    110: 'POP3', 111: 'RPCbind', 123: 'NTP', 135: 'Microsoft RPC',
    137: 'NetBIOS-NS', 138: 'NetBIOS-DGM', 139: 'NetBIOS-SSN', 143: 'IMAP',
    161: 'SNMP', 162: 'SNMPTRAP', 389: 'LDAP', 443: 'HTTPS',
    445: 'Microsoft-DS (SMB)', 500: 'ISAKMP', 514: 'Syslog', 631: 'IPP (CUPS)',
    993: 'IMAPS', 995: 'POP3S', 1080: 'SOCKS', 1433: 'MSSQL',
    1521: 'Oracle', 1701: 'L2TP', 1723: 'PPTP', 3306: 'MySQL',
    3389: 'RDP', 5060: 'SIP', 5061: 'SIPS', 5432: 'PostgreSQL',
    5800: 'VNC-HTTP', 5900: 'VNC', 5901: 'VNC-1', 8000: 'HTTP-Alt',
    8080: 'HTTP-Proxy', 8443: 'HTTPS-Alt'
}

# Global variable to signal the scanning thread to stop
stop_scan_event = threading.Event()
# Queue for port scanning tasks
port_scan_queue = Queue()
# Queue for log messages to be displayed in Gradio UI
log_queue = Queue()

# Global reference to the scan thread
scan_thread_global = None
# Global variable to store current log content for Gradio
current_log_content = ""

def html_log_message(message, color=None):
    """Formats a message with HTML for color."""
    if color:
        return f"<span style='color: {color};'>{message}</span>"
    return message

def add_to_log_queue(message, color=None, clear_first=False):
    """Adds a message to the log_queue for Gradio to pick up."""
    global current_log_content
    log_entry = {"message": html_log_message(message, color), "clear": clear_first}
    log_queue.put(log_entry)

def _check_scapy_and_privileges_gradio():
    """Checks for Scapy and privileges, adds messages to log_queue."""
    global SCAPY_AVAILABLE
    if not SCAPY_AVAILABLE:
        add_to_log_queue("[WARNING] Scapy library not found. Host discovery will be limited. Install with 'pip install scapy'.", "orange")
        # In Gradio, disabling a button would be done by returning gr.update(interactive=False)
        # This function is called at the start, so we'll just log.
    else:
        try:
            if hasattr(os, 'geteuid') and os.geteuid() != 0: # Unix-like, not root
                add_to_log_queue("[INFO] Scapy is available. For ARP-based host discovery, run with root/administrator privileges if you encounter issues.", "blue")
            elif not hasattr(os, 'geteuid'): # Likely Windows
                add_to_log_queue("[INFO] Scapy is available. Ensure Npcap is installed. For ARP discovery, run as Administrator if needed.", "blue")
            else: # Root on Unix
                 add_to_log_queue("[INFO] Scapy available and running with root privileges.", "green")
        except Exception:
            add_to_log_queue("[INFO] Scapy is available. Ensure necessary permissions/drivers for network scanning.", "blue")

def autodiscover_network_gradio():
    """Attempts to discover the local network. Updates log and returns CIDR."""
    if not SCAPY_AVAILABLE:
        add_to_log_queue("[ERROR] Scapy library is required for auto-discovery. Please install it.", "red")
        raise gr.Error("Scapy library is required for auto-discovery. Please install it.")

    add_to_log_queue("[INFO] Attempting to discover local network...", "blue")
    try:
        s_temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_temp.settimeout(0.1)
        try:
            s_temp.connect(('10.255.255.255', 1))
            local_ip = s_temp.getsockname()[0]
        except Exception:
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                local_ip = "127.0.0.1"
        finally:
            s_temp.close()

        if local_ip and local_ip != "127.0.0.1":
            ip_parts = local_ip.split('.')
            if len(ip_parts) == 4:
                network_base = ".".join(ip_parts[:3]) + ".0"
                guessed_network = f"{network_base}/24"
                add_to_log_queue(f"[INFO] Guessed local network: {guessed_network}", "green")
                return guessed_network # Return the network to update the textbox
        add_to_log_queue("[ERROR] Could not automatically determine local network.", "red")
        raise gr.Warning("Could not automatically determine a suitable local network. Please enter manually.")
    except Exception as e:
        add_to_log_queue(f"[ERROR] Auto-discovery failed: {e}", "red")
        raise gr.Error(f"An error occurred during auto-discovery: {e}")
    return "" # Return empty if failed

def get_scan_parameters_gradio(target, port_mode, custom_ports_str, threads_str, timeout_str, no_discover):
    if not target:
        raise gr.Error("Target IP / CIDR cannot be empty.")

    ports_to_scan = []
    if port_mode == "Common Ports":
        ports_to_scan = sorted(COMMON_PORTS.keys())
    elif port_mode == "All Ports (1-65535)":
        ports_to_scan = list(range(1, 65536))
    elif port_mode == "Custom Range":
        try:
            start_port, end_port = map(int, custom_ports_str.split('-'))
            if not (0 < start_port <= end_port <= 65535):
                raise ValueError("Invalid port range values.")
            ports_to_scan = list(range(start_port, end_port + 1))
        except ValueError:
            raise gr.Error("Invalid port range. Use format like '1-1024'.")
    elif port_mode == "Custom List":
        try:
            ports_to_scan = [int(p.strip()) for p in custom_ports_str.split(',') if p.strip()]
            if not all(0 < p <= 65535 for p in ports_to_scan):
                raise ValueError("Invalid port number in list.")
        except ValueError:
            raise gr.Error("Invalid port list. Use comma-separated numbers like '80,443'.")

    if not ports_to_scan:
        raise gr.Error("No ports selected for scanning.")

    try:
        threads = int(threads_str)
        if not (0 < threads <= 500): raise ValueError("Thread count out of range.")
    except ValueError:
        raise gr.Error("Invalid number of threads (must be 1-500).")

    try:
        timeout = float(timeout_str)
        if not (0 < timeout <= 10): raise ValueError("Timeout out of range.")
    except ValueError:
        raise gr.Error("Invalid timeout value (must be >0 and <=10).")

    return {
        "target": target.strip(),
        "ports": ports_to_scan,
        "threads": threads,
        "timeout": timeout,
        "no_discover": no_discover
    }

def _port_scan_worker():
    while not stop_scan_event.is_set():
        try:
            target_ip, port, timeout_val = port_scan_queue.get(timeout=0.1)
        except QueueEmpty:
            if stop_scan_event.is_set() or port_scan_queue.empty(): # Check again to ensure queue is truly empty for this worker
                return # Queue is empty or scan stopped

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_val)
            result = sock.connect_ex((target_ip, port))
            if result == 0:
                service_name = COMMON_PORTS.get(port)
                if not service_name:
                    try: service_name = socket.getservbyport(port)
                    except OSError: service_name = "Unknown"
                add_to_log_queue(f"  [+] IP: {target_ip} - Port {port} is OPEN ({service_name})", "green")
            sock.close()
        except socket.error:
            pass # Port is likely closed or filtered
        except Exception as e:
            add_to_log_queue(f"  [!] Error scanning {target_ip}:{port} - {e}", "red")
        finally:
            port_scan_queue.task_done()
            if 'sock' in locals() and sock:
                try: sock.close()
                except Exception: pass


def _execute_scan_logic(params):
    """The actual scanning logic, run in a thread."""
    ips_to_port_scan = []

    # --- Host Discovery ---
    if "/" in params["target"] and not params["no_discover"]:
        if not SCAPY_AVAILABLE:
            add_to_log_queue("[ERROR] Scapy is required for host discovery on a network range. Please install scapy or use --no-discover with specific IPs.", "red")
            return
        add_to_log_queue(f"[*] Discovering hosts on {params['target']} using ARP (requires privileges if issues)...", "blue")
        try:
            # Note: iface_hint might need to be determined or made configurable for Scapy on some systems.
            # For simplicity, we'll let Scapy try to auto-determine the interface.
            arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=params["target"])
            answered, _ = srp(arp_request, timeout=3, verbose=False) # Removed iface_hint for broader compatibility
            if answered:
                add_to_log_queue(f"[*] Found {len(answered)} live host(s):", "green")
                for _, rcv in answered:
                    if stop_scan_event.is_set(): break
                    ips_to_port_scan.append(rcv.psrc)
                    add_to_log_queue(f"  - {rcv.psrc} ({rcv.hwsrc})")
            else:
                add_to_log_queue("[-] No hosts found via ARP.", "orange")
        except PermissionError:
            add_to_log_queue("[ERROR] Permission denied for ARP scan. Try running with root/administrator privileges.", "red")
            return
        except Exception as e:
            add_to_log_queue(f"[ERROR] Scapy host discovery failed: {e}", "red")
            return

    elif params["no_discover"] and "/" in params["target"]:
        add_to_log_queue(f"[*] Adding all IPs in {params['target']} for port scanning (no host discovery)...", "blue")
        try:
            network = ipaddress.ip_network(params["target"], strict=False)
            for ip_obj in network.hosts():
                if stop_scan_event.is_set(): break
                ips_to_port_scan.append(str(ip_obj))
            if not ips_to_port_scan and network.num_addresses == 1: # e.g., 192.168.1.1/32
                ips_to_port_scan.append(str(network.network_address))
        except ValueError as e:
            add_to_log_queue(f"[ERROR] Invalid target CIDR '{params['target']}': {e}", "red")
            return
    else: # Single IP or comma-separated IPs
        targets = [t.strip() for t in params["target"].split(',') if t.strip()]
        for t_ip in targets:
            try:
                socket.inet_aton(t_ip) # Validate IP
                ips_to_port_scan.append(t_ip)
            except socket.error:
                add_to_log_queue(f"[ERROR] Invalid IP address in target list: {t_ip}", "red")
        if not params["no_discover"] and len(ips_to_port_scan) > 0 : # Check ips_to_port_scan not targets
            add_to_log_queue(f"[*] Target is specific IP(s): {', '.join(ips_to_port_scan)}. Skipping network discovery.", "blue")
        elif not ips_to_port_scan: # If after parsing, no valid IPs are found
            add_to_log_queue("[ERROR] No valid IP addresses provided in target specification.", "red")
            return


    if stop_scan_event.is_set():
        add_to_log_queue("[INFO] Scan stopped during host discovery.", "orange")
        return

    if not ips_to_port_scan:
        add_to_log_queue("[-] No live hosts to scan ports on.", "orange")
        return

    # --- Port Scanning ---
    add_to_log_queue(f"\n[*] Starting port scan on {len(ips_to_port_scan)} host(s) for {len(params['ports'])} port(s) each...", "blue")
    add_to_log_queue(f"     Threads: {params['threads']}, Timeout: {params['timeout']}s", "blue")

    for ip in ips_to_port_scan:
        if stop_scan_event.is_set(): break
        for port in params["ports"]:
            if stop_scan_event.is_set(): break
            port_scan_queue.put((ip, port, params["timeout"]))

    port_threads = []
    for _ in range(params["threads"]):
        if stop_scan_event.is_set(): break
        thread = threading.Thread(target=_port_scan_worker, daemon=True)
        port_threads.append(thread)
        thread.start()

    # Wait for queue to be processed or scan to be stopped
    while not port_scan_queue.empty() and not stop_scan_event.is_set():
        time.sleep(0.2) # Check periodically; log updates happen via log_queue

    if stop_scan_event.is_set():
        add_to_log_queue("[INFO] Attempting to clear remaining port scan queue due to stop signal...", "orange")
        while not port_scan_queue.empty():
            try: port_scan_queue.get_nowait()
            except QueueEmpty: break

    for thread in port_threads:
        # Wait for threads to finish their current task or notice the stop signal.
        # The timeout for join should be related to the task timeout.
        thread.join(timeout=params["timeout"] + 1.0) # Give a bit more time

    if stop_scan_event.is_set():
        add_to_log_queue("[INFO] Scan stopped.", "orange")
    else:
        # This message might be premature if there are still items in log_queue.
        # The main yielding loop handles the "Scan Finished" message more reliably.
        add_to_log_queue("\n--- Scan Potentially Completed (all tasks queued or processed) ---", "green")


def start_scan_gradio(target, port_mode, custom_ports_str, threads_str, timeout_str, no_discover):
    """Gradio interface function to start the scan. Yields log updates."""
    global scan_thread_global, current_log_content

    if scan_thread_global and scan_thread_global.is_alive():
        add_to_log_queue("[INFO] A scan is already running.", "orange")
        # Yield existing logs quickly if start is pressed again
        yield f"<div style='font-family: monospace; white-space: pre-wrap;'>{current_log_content}</div>"
        return

    params = get_scan_parameters_gradio(target, port_mode, custom_ports_str, threads_str, timeout_str, no_discover)
    if not params: # Error handled by get_scan_parameters_gradio raising gr.Error
        yield f"<div style='font-family: monospace; white-space: pre-wrap;'>{current_log_content}</div>" # yield current logs on error
        return

    add_to_log_queue("--- Starting Scan ---", "blue", clear_first=True)
    stop_scan_event.clear()

    # Clear previous port scan queue
    while not port_scan_queue.empty():
        try: port_scan_queue.get_nowait()
        except QueueEmpty: break

    scan_thread_global = threading.Thread(target=_execute_scan_logic, args=(params,), daemon=True)
    scan_thread_global.start()

    # Gradio UI update loop (yielding logs)
    scan_start_time = time.time()
    # Initial log setup for the generator
    processed_initial_logs = False

    while True:
        new_log_entries = []
        while not log_queue.empty():
            log_item = log_queue.get()
            if log_item["clear"] and not processed_initial_logs : # Clear only if it's the very first "clear" instruction
                current_log_content = ""
            current_log_content += log_item["message"] + "<br>"
            log_queue.task_done() # Mark task as done from log_queue
        processed_initial_logs = True # Mark that initial clear (if any) has been processed.

        yield f"<div style='font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto;'>{current_log_content}</div>"

        if not scan_thread_global.is_alive() and port_scan_queue.empty() and log_queue.empty():
            break # Exit loop if scan thread finished and all queues are empty
        time.sleep(0.2) # Interval for UI updates

    # Final log update after scan thread finishes
    add_to_log_queue("--- Scan Finished ---", "blue")
    while not log_queue.empty(): # Process any final messages
        log_item = log_queue.get()
        if log_item["clear"]: current_log_content = "" # Should not happen here ideally
        current_log_content += log_item["message"] + "<br>"
        log_queue.task_done()

    scan_thread_global = None # Reset global thread variable
    yield f"<div style='font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto;'>{current_log_content}</div>"
    # Return button states
    # return gr.Button.update(interactive=True), gr.Button.update(interactive=False) # Re-enable Start, Disable Stop

def stop_scan_action_gradio():
    global scan_thread_global
    if scan_thread_global and scan_thread_global.is_alive():
        add_to_log_queue("[INFO] Stop signal sent. Waiting for threads to finish current tasks...", "orange")
        stop_scan_event.set()
        # Buttons will be updated by the start_scan_gradio completion or if we want immediate feedback:
        # return gr.Button.update(interactive=False), gr.Button.update(interactive=True) # Disable Stop, Enable Start (might be too soon)
        return "Stop signal sent. Monitor logs." # Simple message for now
    else:
        add_to_log_queue("[INFO] No active scan to stop.", "blue")
        return "No active scan to stop."


# Initialize log content with Scapy/privilege checks
_check_scapy_and_privileges_gradio()
initial_logs_for_display = ""
while not log_queue.empty():
    log_item = log_queue.get()
    if log_item["clear"]: initial_logs_for_display = ""
    initial_logs_for_display += log_item["message"] + "<br>"
    log_queue.task_done()
current_log_content = "Welcome to LAN Scanner for breaking circuits llc. Please configure and start the scan.<br>" + initial_logs_for_display


# --- Gradio Interface Definition ---
with gr.Blocks(theme=gr.themes.Soft(), title="LAN IP & Port Scanner (breaking circuits llc)") as demo:
    gr.Markdown("# LAN IP & Port Scanner\nFor breaking circuits llc")

    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("## Target Configuration")
            with gr.Row():
                target_entry = gr.Textbox(label="Target IP / CIDR", placeholder="e.g., 192.168.1.0/24, 10.0.0.5", info="Enter target IP, comma-separated IPs, or CIDR.")
                autodiscover_button = gr.Button("Auto-Discover Local Network", variant="secondary", size="sm")

            gr.Markdown("## Port Configuration")
            port_mode_radio = gr.Radio(
                ["Common Ports", "All Ports (1-65535)", "Custom Range", "Custom List"],
                label="Port Scan Mode",
                value="Common Ports",
                info="Select which ports to scan."
            )
            custom_ports_entry = gr.Textbox(
                label="Custom Ports",
                placeholder="e.g., 1-1024 or 80,443,8080",
                value="1-1024",
                visible=False, # Initially hidden
                info="Define custom ports if 'Custom Range' or 'Custom List' is selected."
            )

            def toggle_custom_ports_entry(mode):
                if mode == "Custom Range" or mode == "Custom List":
                    return gr.Textbox(visible=True)
                return gr.Textbox(visible=False)

            port_mode_radio.change(fn=toggle_custom_ports_entry, inputs=port_mode_radio, outputs=custom_ports_entry)

        with gr.Column(scale=2):
            gr.Markdown("## Scan Options")
            threads_entry = gr.Textbox(label="Threads", value="50", info="Number of concurrent scanning threads (1-500).")
            timeout_entry = gr.Textbox(label="Timeout (s)", value="0.5", info="Connection timeout per port in seconds (0.1-10).")
            no_discover_check = gr.Checkbox(label="Skip Host Discovery (Target must be IP(s) or for full CIDR scan)", value=False, info="If checked, directly scans all IPs in CIDR or specified IPs without ARP ping.")

    with gr.Row():
        start_button = gr.Button("Start Scan", variant="primary")
        stop_button = gr.Button("Stop Scan", variant="stop", interactive=True) # Start enabled, will be managed by running scan

    gr.Markdown("## Scan Output")
    output_text_html = gr.HTML(value=f"<div style='font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto;'>{current_log_content}</div>")

    # --- Event Handlers ---
    autodiscover_button.click(
        fn=autodiscover_network_gradio,
        inputs=None,
        outputs=[target_entry] # Updates the target_entry textbox
        # Log updates from autodiscover_network_gradio are handled via the shared log_queue and yielded by start_scan_gradio
    )

    start_event = start_button.click(
        fn=start_scan_gradio,
        inputs=[target_entry, port_mode_radio, custom_ports_entry, threads_entry, timeout_entry, no_discover_check],
        outputs=[output_text_html] # output_text_html will be updated by yields
    )
    # After start_scan_gradio finishes (or is cancelled), we might want to update button states.
    # This can be done by returning gr.update() values from the function for each button.
    # For simplicity, Gradio's default behavior where buttons are disabled during function execution is often sufficient.
    # However, for long-running yield-based functions, more explicit control might be desired via gr.State or by returning updates.

    stop_button.click(
        fn=stop_scan_action_gradio,
        inputs=None,
        outputs=None, # Could output to a small status message, but logs are primary
        cancels=[start_event] # This is crucial to stop the yielding loop of start_scan_gradio
    )

if __name__ == "__main__":
    demo.queue() # Enable queue for handling multiple users/requests and long-running tasks properly.
    demo.launch()