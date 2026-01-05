import json
from pathlib import Path
from typing import Optional, Union

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static, TabbedContent, TabPane, Tab, Tabs

from tappet.http_client import execute_request
from tappet.models import RequestSet, Response
from tappet.store import RequestSetStore
from tappet.utils.editor import open_in_editor


class RequestListWidget(ListView):
    can_focus = True
    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("n", "new_request", "New"),
        ("c", "copy_request", "Copy"),
        ("d", "delete_request", "Delete"),
        ("e", "edit_request", "Edit"),
        ("enter", "run_request", "Run"),
    ]

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

    def action_copy_request(self) -> None:
        request_set = self.store.get_selected()
        if request_set is None:
            return
        self.store.copy(request_set)

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


class DetailPanelWidget(Container):
    can_focus = True
    BINDINGS = [
        ("h", "prev_tab", "Prev Tab"),
        ("left", "prev_tab", "Prev Tab"),
        ("l", "next_tab", "Next Tab"),
        ("right", "next_tab", "Next Tab"),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent(id="detail-tabs", initial="detail-tab-info"):
            with TabPane("Info", id="detail-tab-info"):
                yield VerticalScroll(Static(id="detail-info"))
            with TabPane("Request Body", id="detail-tab-body"):
                yield VerticalScroll(Static(id="detail-body"))
            with TabPane("Request Headers", id="detail-tab-headers"):
                yield VerticalScroll(Static(id="detail-headers"))

    def on_mount(self) -> None:
        tabbed = self.query_one(TabbedContent)
        tabbed.can_focus = False
        for tabs in tabbed.query(Tabs):
            tabs.can_focus = False
        for tab in tabbed.query(Tab):
            tab.can_focus = False
        for scroll in tabbed.query(VerticalScroll):
            scroll.can_focus = False

    def set_content(self, request_set: Optional[RequestSet]) -> None:
        self.query_one("#detail-info", Static).update(self._format_request_info(request_set))
        self.query_one("#detail-headers", Static).update(self._format_request_headers(request_set))
        self.query_one("#detail-body", Static).update(self._format_request_body(request_set))

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def action_prev_tab(self) -> None:
        self._switch_tab(-1)

    def _switch_tab(self, offset: int) -> None:
        tab_ids = ("detail-tab-info", "detail-tab-body", "detail-tab-headers")
        tabbed = self.query_one(TabbedContent)
        active_id = tabbed.active
        current_index = tab_ids.index(active_id) if active_id in tab_ids else 0
        next_index = (current_index + offset) % len(tab_ids)
        tabbed.active = tab_ids[next_index]

    def _format_request_info(self, request_set: Optional[RequestSet]) -> Union[Text, str]:
        if request_set is None:
            return "(No request selected)"
        description = request_set.description if request_set.description else "-"
        method_text = request_set.method.upper()
        method_color = {"GET": "green", "POST": "yellow"}.get(method_text)
        text = Text()
        if method_color:
            text.append(method_text, style=method_color)
        else:
            text.append(method_text)
        text.append(f" {request_set.url}\n")
        text.append(description)
        return text

    def _format_request_headers(self, request_set: Optional[RequestSet]) -> str:
        if request_set is None:
            return "(none)"
        headers_text = "\n".join(f"{key}: {value}" for key, value in request_set.headers.items())
        return headers_text if headers_text else "(none)"

    def _format_request_body(self, request_set: Optional[RequestSet]) -> str:
        if request_set is None:
            return "(empty)"
        if request_set.body:
            return json.dumps(request_set.body, indent=2, ensure_ascii=False)
        return "(empty)"


class ResponsePanelWidget(Container):
    can_focus = True
    BINDINGS = [
        ("h", "prev_tab", "Prev Tab"),
        ("left", "prev_tab", "Prev Tab"),
        ("l", "next_tab", "Next Tab"),
        ("right", "next_tab", "Next Tab"),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent(id="response-tabs", initial="response-tab-main"):
            with TabPane("Status/Body", id="response-tab-main"):
                yield VerticalScroll(Static(id="response-main"))
            with TabPane("Response Headers", id="response-tab-headers"):
                yield VerticalScroll(Static(id="response-headers"))

    def on_mount(self) -> None:
        tabbed = self.query_one(TabbedContent)
        tabbed.can_focus = False
        for tabs in tabbed.query(Tabs):
            tabs.can_focus = False
        for tab in tabbed.query(Tab):
            tab.can_focus = False
        for scroll in tabbed.query(VerticalScroll):
            scroll.can_focus = False

    def set_content(self, response: Optional[Response]) -> None:
        self.query_one("#response-main", Static).update(self._format_response_status_body(response))
        self.query_one("#response-headers", Static).update(self._format_response_headers(response))

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def action_prev_tab(self) -> None:
        self._switch_tab(-1)

    def _switch_tab(self, offset: int) -> None:
        tab_ids = ("response-tab-main", "response-tab-headers")
        tabbed = self.query_one(TabbedContent)
        active_id = tabbed.active
        current_index = tab_ids.index(active_id) if active_id in tab_ids else 0
        next_index = (current_index + offset) % len(tab_ids)
        tabbed.active = tab_ids[next_index]

    def _format_response_status_body(self, response: Optional[Response]) -> str:
        if response is None:
            return "(not run)"
        if response.note:
            return response.note
        if response.error:
            return f"Error: {response.error}"
        body_text = self._format_response_body(response)
        status_line = "Status: (unknown)"
        if response.status_code is not None:
            reason = f" {response.reason}" if response.reason else ""
            elapsed = ""
            if response.elapsed_ms is not None:
                elapsed = f" ({response.elapsed_ms:.0f} ms)"
            status_line = f"Status: {response.status_code}{reason}{elapsed}"
        return f"{status_line}\n\n{body_text}"

    def _format_response_headers(self, response: Optional[Response]) -> str:
        if response is None:
            return "(none)"
        headers_text = "\n".join(f"{key}: {value}" for key, value in (response.headers or {}).items())
        return headers_text if headers_text else "(none)"

    def _format_response_body(self, response: Response) -> str:
        body_text = response.body if response.body else ""
        if body_text:
            content_type = ""
            if response.headers:
                content_type = response.headers.get("Content-Type", "")
            should_format_json = "application/json" in content_type.lower()
            if should_format_json or body_text.strip().startswith(("{", "[")):
                try:
                    body_text = json.dumps(json.loads(body_text), indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
        if not body_text:
            body_text = "(empty)"
        if len(body_text) > 4000:
            body_text = body_text[:4000] + "\n... (truncated)"
        return body_text


class ConfirmDeleteScreen(ModalScreen[bool]):
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
    CSS_PATH = "themes/default.css"
    TITLE = "tappet"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
    ]

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
                RequestListWidget(self.store, id="left-panel"),
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

    async def on_request_list_widget_run_requested(self, message: RequestListWidget.RunRequested) -> None:
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
