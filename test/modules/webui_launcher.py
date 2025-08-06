import subprocess
import sys
import os

_webui_proc = None

def launch(ip: str = "127.0.0.1", port: int = 7788, theme: str = "Ocean") -> str:
    """Launch Gradio web UI from webui.py as background process."""
    global _webui_proc
    if _webui_proc is not None and _webui_proc.poll() is None:
        return f"Web UI is already running at http://{ip}:{port} (theme: {theme})"
    script_path = os.path.abspath("webui.py")
    if not os.path.exists(script_path):
        raise ImportError("webui.py not found. Please ensure it exists in the project root.")
    try:
        _webui_proc = subprocess.Popen(
            [sys.executable, script_path, "--ip", ip, "--port", str(port), "--theme", theme],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return f"Web UI launched at http://{ip}:{port} (theme: {theme})"
    except Exception as e:
        raise RuntimeError(f"Failed to launch webui.py: {e}")