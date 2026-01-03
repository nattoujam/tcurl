import json
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from tcurl.http_client import execute_request
from tcurl.models import RequestSet, Response
from tcurl.storage.requests import (
    create_request_set,
    delete_request_set,
    load_request_sets,
)
from tcurl.utils.editor import open_in_editor


class RequestListWidget(ListView):
    can_focus = True
    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]
    DEFAULT_CSS = """
    RequestListWidget {
        width: 30%;
        border: solid green;
    }

    RequestListWidget:focus {
        border: solid yellow;
    }
    """


class DetailPanelWidget(Static):
    can_focus = True
    DEFAULT_CSS = """
    DetailPanelWidget {
        border: solid blue;
        padding: 1 2;
    }

    DetailPanelWidget:focus {
        border: solid yellow;
    }
    """


class ResponsePanelWidget(VerticalScroll):
    can_focus = True
    DEFAULT_CSS = """
    ResponsePanelWidget {
        border: solid cyan;
        padding: 1 2;
    }

    ResponsePanelWidget:focus {
        border: solid yellow;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="response-content")

    def set_content(self, response: Optional[Response]) -> None:
        self.query_one("#response-content", Static).update(
            self._format_response_details(response)
        )

    def _format_response_details(self, response: Optional[Response]) -> str:
        if response is None:
            return "Response\n\n(not run)"
        if response.note:
            return f"Response\n\n{response.note}"
        if response.error:
            return f"Response\n\nError: {response.error}"
        body_text = self._format_response_body(response)
        status_line = "Status: (unknown)"
        if response.status_code is not None:
            reason = f" {response.reason}" if response.reason else ""
            elapsed = ""
            if response.elapsed_ms is not None:
                elapsed = f" ({response.elapsed_ms:.0f} ms)"
            status_line = f"Status: {response.status_code}{reason}{elapsed}"
        headers_text = "\n".join(
            f"{key}: {value}" for key, value in (response.headers or {}).items()
        )
        if not headers_text:
            headers_text = "(none)"
        return (
            "Response\n\n"
            f"{status_line}\n\n"
            "[Headers]\n"
            f"{headers_text}\n\n"
            "[Body]\n"
            f"{body_text}"
        )

    def _format_response_body(self, response: Response) -> str:
        body_text = response.body if response.body else ""
        if body_text:
            content_type = ""
            if response.headers:
                content_type = response.headers.get("Content-Type", "")
            should_format_json = "application/json" in content_type.lower()
            if should_format_json or body_text.strip().startswith(("{", "[")):
                try:
                    body_text = json.dumps(
                        json.loads(body_text), indent=2, ensure_ascii=True
                    )
                except json.JSONDecodeError:
                    pass
        if not body_text:
            body_text = "(empty)"
        if len(body_text) > 4000:
            body_text = body_text[:4000] + "\n... (truncated)"
        return body_text


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
        ("enter", "run_request", "Run"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
    }

    #right-panel {
        width: 70%;
        layout: vertical;
        height: 1fr;
    }

    #detail-panel {
        height: 1fr;
    }

    #response-panel {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.request_sets: list[RequestSet] = []
        self.responses: dict[str, Response] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                RequestListWidget(id="request-list"),
                Container(
                    DetailPanelWidget(id="detail-panel"),
                    ResponsePanelWidget(id="response-panel"),
                    id="right-panel",
                ),
                id="main",
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        self._reload_request_list()
        self.query_one(RequestListWidget).focus()

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

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self.request_sets:
            return
        if event.control.index >= len(self.request_sets):
            return
        await self.action_run_request()

    def action_new_request(self) -> None:
        created = create_request_set()
        self._reload_request_list(select_path=created.file_path)

    def action_delete_request(self) -> None:
        request_set = self._get_selected_request_set()
        if request_set is None:
            return
        message = f"{request_set.name}を削除しますか？ (y/n)"
        self.push_screen(
            ConfirmDeleteScreen(message),
            lambda confirmed: self._delete_request(request_set, confirmed),
        )

    def action_edit_request(self) -> None:
        request_set = self._get_selected_request_set()
        if request_set is None:
            return
        if request_set.file_path is None:
            return
        self._open_editor(request_set.file_path)
        self._reload_request_list(select_path=request_set.file_path)

    async def action_run_request(self) -> None:
        request_set = self._get_selected_request_set()
        if request_set is None:
            return
        self.responses[self._response_key(request_set)] = Response(
            note="Running..."
        )
        self._show_request_details(request_set)
        self.responses[self._response_key(request_set)] = await execute_request(
            request_set
        )
        if self._is_selected(request_set):
            self._show_request_details(request_set)

    def _show_request_details(self, request_set: Optional[RequestSet]) -> None:
        detail_panel = self.query_one(DetailPanelWidget)
        response_panel = self.query_one(ResponsePanelWidget)
        if request_set is None:
            detail_panel.update("Request Details\n\n(No request selected)")
            response_panel.set_content(None)
            return
        detail_panel.update(self._format_request_details(request_set))
        response_panel.set_content(
            self.responses.get(self._response_key(request_set))
        )

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

    def _get_selected_request_set(self) -> Optional[RequestSet]:
        if not self.request_sets:
            return None
        request_list = self.query_one(RequestListWidget)
        if request_list.highlighted_child is None:
            return None
        if request_list.index >= len(self.request_sets):
            return None
        return self.request_sets[request_list.index]

    def _is_selected(self, request_set: RequestSet) -> bool:
        selected = self._get_selected_request_set()
        return selected is request_set

    def _response_key(self, request_set: RequestSet) -> str:
        if request_set.file_path is not None:
            return str(request_set.file_path)
        return request_set.name

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
