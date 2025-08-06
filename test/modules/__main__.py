import sys

def main():
    # Launch root CLI (ada) by default
    try:
        from modules.root_cli import app
        import typer
        typer.run(app)
    except Exception as e:
        print(f"Error launching Ada CLI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()