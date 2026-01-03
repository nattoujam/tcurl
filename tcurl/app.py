import json
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from tcurl.http_client import execute_request
from tcurl.models import RequestSet, Response
from tcurl.store import RequestSetStore
from tcurl.utils.editor import open_in_editor


class RequestListWidget(ListView):
    can_focus = True
    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("n", "new_request", "New"),
        ("d", "delete_request", "Delete"),
        ("e", "edit_request", "Edit"),
        ("enter", "run_request", "Run"),
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

    class RunRequested(Message):
        def __init__(self, request_set: RequestSet) -> None:
            super().__init__()
            self.request_set = request_set

    def __init__(self, store: RequestSetStore, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.store = store
        self.request_sets: list[RequestSet] = []
        self.store.subscribe_items(self._on_items_change)
        self.store.subscribe_selection(self._on_selection_change)

    def _on_items_change(self, select_set: Optional[RequestSet]) -> None:
        self.clear()
        self.request_sets = self.store.items
        if not self.request_sets:
            self.append(ListItem(Label("no requests found")))
            return

        selected_index: Optional[int] = None
        for index, request_set in enumerate(self.request_sets):
            self.append(ListItem(Label(request_set.name)))
            if select_set is not None and request_set == select_set:
                selected_index = index

        if selected_index is None:
            selected_index = 0
        self.index = selected_index

    def _on_selection_change(self, select_set: Optional[RequestSet]) -> None:
        if not self.request_sets or select_set is None:
            return
        for index, request_set in enumerate(self.request_sets):
            if request_set == select_set:
                self.index = index
                break

    def get_selected_request_set(self) -> Optional[RequestSet]:
        return self.store.get_selected()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if self.index is None:
            return
        if self.index < 0 or self.index >= len(self.request_sets):
            return
        self.store.set_selected(self.request_sets[self.index])

    def action_new_request(self) -> None:
        self.store.create()

    def action_delete_request(self) -> None:
        request_set = self.store.get_selected()
        if request_set is None:
            return
        self.app.push_screen(ConfirmDeleteScreen(request_set, self.store.delete))

    def action_edit_request(self) -> None:
        request_set = self.store.get_selected()
        if request_set is None:
            return
        if request_set.file_path is None:
            return
        self._open_editor(request_set.file_path)
        self.store.refresh(select_set=request_set)

    def action_run_request(self) -> None:
        request_set = self.store.get_selected()
        if request_set is None:
            return
        self.post_message(self.RunRequested(request_set))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.action_run_request()

    def _open_editor(self, path: Path) -> None:
        app = self.app
        if app is None or app._driver is None:
            open_in_editor(path)
            return
        app._driver.stop_application_mode()
        try:
            open_in_editor(path)
        finally:
            app._driver.start_application_mode()
            app.refresh(layout=True)


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

    def set_content(self, request_set: Optional[RequestSet]) -> None:
        if request_set is None:
            self.update("Request Details\n\n(No request selected)")
            return
        self.update(self._format_request_details(request_set))

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

    def __init__(self, request_set: RequestSet, on_confirm) -> None:
        super().__init__()
        self.request_set = request_set
        self.on_confirm = on_confirm

    def compose(self) -> ComposeResult:
        message = f"{self.request_set.name}を削除しますか？ (y/n)"
        yield Container(
            Static(message, id="confirm-message"),
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
        self.on_confirm(self.request_set)
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class TcurlApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
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
        self.store = RequestSetStore()
        self.store.subscribe_selection(self._on_selection_change)
        self.detail_panel: Optional[DetailPanelWidget] = None
        self.response_panel: Optional[ResponsePanelWidget] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Horizontal(
                RequestListWidget(self.store, id="request-list"),
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
        request_list = self.query_one(RequestListWidget)
        self.detail_panel = self.query_one(DetailPanelWidget)
        self.response_panel = self.query_one(ResponsePanelWidget)
        self.store.refresh()
        request_list.focus()

    async def on_request_list_widget_run_requested(
        self, message: RequestListWidget.RunRequested
    ) -> None:
        request_set = message.request_set
        self.store.set_response(request_set, Response(note="Running..."))
        self._show_request_details(request_set)
        response = await execute_request(request_set)
        self.store.set_response(request_set, response)
        if self._is_selected(request_set):
            self._show_request_details(request_set)

    def _show_request_details(self, request_set: Optional[RequestSet]) -> None:
        detail_panel = self.detail_panel
        response_panel = self.response_panel
        if detail_panel is None or response_panel is None:
            return
        if request_set is None:
            detail_panel.set_content(None)
            response_panel.set_content(None)
            return
        detail_panel.set_content(request_set)
        response_panel.set_content(self.store.get_response(request_set))

    def _on_selection_change(self, select_set: Optional[RequestSet]) -> None:
        self._show_request_details(select_set)

    def _is_selected(self, request_set: RequestSet) -> bool:
        return self.store.get_selected() is request_set
