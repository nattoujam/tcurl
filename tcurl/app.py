from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from tcurl.models import RequestSet
from tcurl.storage import create_request_set, delete_request_set, load_request_sets
from tcurl.utils.editor import open_in_editor


class RequestListWidget(ListView):
    """Left panel for request sets."""


class DetailPanelWidget(Static):
    """Right panel for request details and response."""


class ConfirmDeleteScreen(ModalScreen[bool]):
    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }

    #confirm-dialog {
        layout: vertical;
        width: auto;
        min-width: 32;
        max-width: 60;
        height: auto;
        padding: 1 2;
        border: solid $primary;
        background: $panel;
        align: center middle;
    }

    #confirm-message {
        text-align: center;
        content-align: center middle;
    }

    #confirm-buttons {
        margin-top: 1;
        width: auto;
        height: auto;
        align: center middle;
    }

    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("escape", "cancel", "No"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.message, id="confirm-message"),
            Horizontal(
                Button("Yes", id="confirm-yes"),
                Button("No", id="confirm-no"),
                id="confirm-buttons",
            ),
            id="confirm-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class TcurlApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_request", "New"),
        ("d", "delete_request", "Delete"),
        ("e", "edit_request", "Edit"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
    }

    #request-list {
        width: 30%;
        border: solid green;
    }

    #detail-panel {
        width: 70%;
        border: solid blue;
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.request_sets: list[RequestSet] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                RequestListWidget(id="request-list"),
                DetailPanelWidget(id="detail-panel"),
                id="main",
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self._reload_request_list()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if not self.request_sets:
            return
        list_view = event.control
        if list_view.highlighted_child is None:
            self._show_request_details(None)
            return
        if list_view.index >= len(self.request_sets):
            return
        self._show_request_details(self.request_sets[list_view.index])

    def action_new_request(self) -> None:
        created = create_request_set()
        self._reload_request_list(select_path=created.file_path)

    def action_delete_request(self) -> None:
        if not self.request_sets:
            return
        request_list = self.query_one(RequestListWidget)
        if request_list.highlighted_child is None:
            return
        if request_list.index >= len(self.request_sets):
            return

        request_set = self.request_sets[request_list.index]
        message = f"{request_set.name}を削除しますか？ (y/n)"
        self.push_screen(
            ConfirmDeleteScreen(message),
            lambda confirmed: self._delete_request(request_set, confirmed),
        )

    def action_edit_request(self) -> None:
        if not self.request_sets:
            return
        request_list = self.query_one(RequestListWidget)
        if request_list.highlighted_child is None:
            return
        if request_list.index >= len(self.request_sets):
            return
        request_set = self.request_sets[request_list.index]
        if request_set.file_path is None:
            return
        self._open_editor(request_set.file_path)
        self._reload_request_list(select_path=request_set.file_path)

    def _show_request_details(self, request_set: Optional[RequestSet]) -> None:
        detail_panel = self.query_one(DetailPanelWidget)
        if request_set is None:
            detail_panel.update("Request Details\n\n(No request selected)")
            return
        detail_panel.update(self._format_request_details(request_set))

    def _delete_request(self, request_set: RequestSet, confirmed: Optional[bool]) -> None:
        if not confirmed:
            return
        delete_request_set(request_set)
        self._reload_request_list()

    def _open_editor(self, path: Path) -> None:
        if self._driver is None:
            open_in_editor(path)
            return
        self._driver.stop_application_mode()
        try:
            open_in_editor(path)
        finally:
            self._driver.start_application_mode()
            self.refresh(layout=True)

    def _reload_request_list(self, select_path: Optional[Path] = None) -> None:
        request_list = self.query_one(RequestListWidget)
        request_list.clear()
        self.request_sets = load_request_sets()
        if not self.request_sets:
            request_list.append(ListItem(Label("no requests found")))
            self._show_request_details(None)
            return

        selected_index: Optional[int] = None
        for index, request_set in enumerate(self.request_sets):
            request_list.append(ListItem(Label(request_set.name)))
            if select_path and request_set.file_path == select_path:
                selected_index = index

        if selected_index is None:
            selected_index = 0
        request_list.index = selected_index
        self._show_request_details(self.request_sets[selected_index])

    def _format_request_details(self, request_set: RequestSet) -> str:
        headers_text = "\n".join(
            f"{key}: {value}" for key, value in request_set.headers.items()
        )
        if not headers_text:
            headers_text = "(none)"
        body_text = request_set.body if request_set.body else "(empty)"
        description = request_set.description if request_set.description else "-"
        return (
            "Request Details\n\n"
            f"Name: {request_set.name}\n"
            f"Method: {request_set.method}\n"
            f"URL: {request_set.url}\n"
            f"Description: {description}\n\n"
            "[Headers]\n"
            f"{headers_text}\n\n"
            "[Body]\n"
            f"{body_text}"
        )
