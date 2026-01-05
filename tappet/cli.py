import click

from tappet.app import TcurlApp


@click.command()
def main() -> None:
    """Run the tappet TUI application."""
    app = TcurlApp()
    app.run()


if __name__ == "__main__":
    main()
