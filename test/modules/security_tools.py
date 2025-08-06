import subprocess, shutil, os, sys, requests
import json

def nmap_scan(target: str, flags: str = "-sV -T4") -> str:
    if shutil.which("nmap") is None:
        return "Error: nmap not installed."
    try:
        cmd = ["nmap"] + flags.split() + [target]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return res.stdout or res.stderr
    except Exception as e:
        return f"nmap scan error: {e}"

def nikto_scan(url: str, options: str = "") -> str:
    if shutil.which("nikto") is None:
        return "Error: nikto not installed."
    try:
        cmd = ["nikto", "-h", url] + (options.split() if options else [])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return res.stdout or res.stderr
    except Exception as e:
        return f"nikto scan error: {e}"

def wapiti_scan(url: str, scope: str = "folder") -> str:
    if shutil.which("wapiti") is None:
        return "Error: wapiti not installed."
    try:
        cmd = ["wapiti", "-u", url, "-r", "5", "-s", scope]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return res.stdout or res.stderr
    except Exception as e:
        return f"wapiti scan error: {e}"

def shodan_lookup(query: str) -> str:
    try:
        import shodan
    except ImportError:
        return "shodan package not installed."
    api_key = os.getenv("SHODAN_API_KEY")
    if not api_key:
        return "SHODAN_API_KEY not set."
    try:
        api = shodan.Shodan(api_key)
        result = api.search(query)
        out = f"Results: {result['total']} matches\n"
        for match in result["matches"][:3]:
            out += f"IP: {match.get('ip_str','')} | Ports: {match.get('port','')} | Data: {match.get('data','')[:120]}...\n"
        return out
    except Exception as e:
        return f"Shodan error: {e}"

def censys_lookup(ip: str) -> str:
    try:
        from censys.search import CensysHosts
    except ImportError:
        return "censys-search package not installed."
    api_id = os.getenv("CENSYS_API_ID")
    api_secret = os.getenv("CENSYS_API_SECRET")
    if not api_id or not api_secret:
        return "CENSYS_API_ID or CENSYS_API_SECRET not set."
    try:
        c = CensysHosts(api_id, api_secret)
        res = c.search(ip)
        return json.dumps(res, indent=2) if res else f"No info found for {ip}."
    except Exception as e:
        return f"Censys error: {e}"

def exploit_search(keyword: str) -> str:
    # Try local searchsploit, else fallback to online ExploitDB
    if shutil.which("searchsploit"):
        try:
            cmd = ["searchsploit", keyword]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return res.stdout or res.stderr
        except Exception as e:
            return f"searchsploit error: {e}"
    else:
        try:
            url = f"https://www.exploit-db.com/search?order_by=date_published&order=desc&text={keyword}"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                # crude parse for result text
                return f"Results page: {url} (open in browser for details)"
            else:
                return f"ExploitDB web search failed: {resp.status_code}"
        except Exception as e:
            return f"ExploitDB error: {e}"