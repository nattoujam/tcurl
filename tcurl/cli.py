import click

from tcurl.app import TcurlApp


@click.command()
def main() -> None:
    """Run the tcurl TUI application."""
    app = TcurlApp()
    app.run()


if __name__ == "__main__":
    main()
