from modules.celery_app import celery_app
from modules.ipport_wrapper import scan as ip_scan
from modules.security_tools import nmap_scan

@celery_app.task(name="ip_port_scan")
def ip_port_scan_task(target, port_mode, custom_ports, threads, timeout, no_discover):
    return ip_scan(target, port_mode, custom_ports, threads, timeout, no_discover)

@celery_app.task(name="nmap_scan")
def nmap_scan_task(target, flags):
    return nmap_scan(target, flags)