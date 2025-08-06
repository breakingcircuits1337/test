import sys

def main():
    # Launch Web UI by default; fallback to voice_chat
    try:
        from commands import template
        import typer
        # try to launch webui; fallback to voice_chat if fails
        try:
            typer.run(template.launch_webui)
        except Exception:
            typer.run(template.voice_chat)
    except Exception as e:
        print(f"Error launching Ada: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()