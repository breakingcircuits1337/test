import re

def scan(target: str,
         port_mode: str = "Common Ports",
         custom_ports: str = "",
         threads: int = 50,
         timeout: float = 0.5,
         no_discover: bool = False) -> str:
    """
    Run the LAN scanner head-less, return plain text results.
    Args:
        target: IP, CIDR, or comma-separated list
        port_mode: "Common Ports", "All Ports (1-65535)", "Custom Range", "Custom List"
        custom_ports: e.g. "1-1024" or "80,443"
        threads: 1-500
        timeout: float(seconds)
        no_discover: skip ARP discovery
    Returns:
        Plain text scan log
    """
    try:
        import sys
        import os
        import importlib
        from queue import Empty as QueueEmpty
        ipport = importlib.import_module("ipport")
    except ImportError:
        raise ImportError("ipport.py (and gradio) are required for LAN scanning. Please ensure gradio is installed.")

    # Validate parameters using ipport's UI validation
    params = ipport.get_scan_parameters_gradio(
        target,
        port_mode,
        custom_ports,
        str(threads),
        str(timeout),
        no_discover
    )

    # Clear port scan and log queues before run
    while not ipport.port_scan_queue.empty():
        try: ipport.port_scan_queue.get_nowait()
        except QueueEmpty: break
    while not ipport.log_queue.empty():
        try: ipport.log_queue.get_nowait()
        except QueueEmpty: break

    # Clear stop event
    if hasattr(ipport, 'stop_scan_event'):
        ipport.stop_scan_event.clear()

    # Run scan in thread, wait for completion
    import threading
    scan_thread = threading.Thread(target=ipport._execute_scan_logic, args=(params,), daemon=True)
    scan_thread.start()
    scan_thread.join()  # Block until scan completes

    # Gather log messages
    results = []
    while not ipport.log_queue.empty():
        log_item = ipport.log_queue.get()
        msg = log_item["message"]
        # Remove HTML tags (span, br, etc)
        msg = re.sub(r'<[^>]+>', '', msg)
        results.append(msg)
        ipport.log_queue.task_done()
    # Also drain port_scan_queue if any remain
    while not ipport.port_scan_queue.empty():
        try: ipport.port_scan_queue.get_nowait()
        except QueueEmpty: break

    return "\n".join(results)