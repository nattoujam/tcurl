from __future__ import annotations

from typing import Callable, Optional

from tappet.models import RequestSet, Response
from tappet.storage.requests import create_request_set, delete_request_set, duplicate_request_set, load_request_sets


StoreCallback = Callable[[Optional[RequestSet]], None]


class RequestSetStore:
    def __init__(self) -> None:
        self.items: list[RequestSet] = []
        self.selected_set: Optional[RequestSet] = None
        self._responses: dict[str, Response] = {}
        self._items_callbacks: list[StoreCallback] = []
        self._selection_callbacks: list[StoreCallback] = []

    def subscribe_items(self, callback: StoreCallback) -> None:
        self._items_callbacks.append(callback)

    def subscribe_selection(self, callback: StoreCallback) -> None:
        self._selection_callbacks.append(callback)

    def _notify_items(self, select_set: Optional[RequestSet] = None) -> None:
        for callback in self._items_callbacks:
            callback(select_set)

    def _notify_selection(self, select_set: Optional[RequestSet] = None) -> None:
        for callback in self._selection_callbacks:
            callback(select_set)

    def refresh(self, select_set: Optional[RequestSet] = None) -> None:
        self.items = load_request_sets()
        self._decide_selection(select_set)
        self._prune_responses()
        self._notify_items(self.selected_set)
        self._notify_selection(self.selected_set)

    def create(self) -> Optional[RequestSet]:
        created = create_request_set()
        if created is None:
            return None
        self.refresh(select_set=created)
        return created

    def copy(self, request_set: RequestSet) -> Optional[RequestSet]:
        if not self._is_in_items(request_set):
            return None
        created = duplicate_request_set(request_set)
        if created is None:
            return None
        self.refresh(select_set=created)
        return created

    def delete(self, request_set: RequestSet) -> None:
        delete_request_set(request_set)
        self.refresh()

    def set_selected(self, request_set: RequestSet) -> Optional[RequestSet]:
        if not self._is_in_items(request_set):
            return None
        if request_set == self.selected_set:
            return request_set
        self.selected_set = request_set
        self._notify_selection(self.selected_set)
        return request_set

    def get_selected(self) -> Optional[RequestSet]:
        return self.selected_set

    def set_response(self, request_set: RequestSet, response: Response) -> None:
        if not self._is_in_items(request_set):
            return
        self._responses[self._response_key(request_set)] = response

    def get_response(self, request_set: RequestSet) -> Optional[Response]:
        if not self._is_in_items(request_set):
            return None
        return self._responses.get(self._response_key(request_set))

    def _decide_selection(self, select_set: Optional[RequestSet]) -> None:
        if select_set is not None:
            if self._is_in_items(select_set):
                self.selected_set = select_set
                return
        if self.selected_set is not None:
            if self._is_in_items(self.selected_set):
                return
        self.selected_set = self.items[0] if self.items else None

    def _is_in_items(self, request_set: RequestSet) -> bool:
        for item in self.items:
            if item == request_set:
                return True
        return False

    def _prune_responses(self) -> None:
        if not self._responses:
            return
        valid_keys = {self._response_key(item) for item in self.items}
        self._responses = {key: response for key, response in self._responses.items() if key in valid_keys}

    def _response_key(self, request_set: RequestSet) -> str:
        if request_set.file_path is not None:
            return str(request_set.file_path)
        return request_set.name
