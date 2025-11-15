from abc import ABC, abstractmethod
from typing import Callable, Optional

from prompt_toolkit.shortcuts import choice

from core.utils import cls


class NavigationNode(ABC):

    def __init__(self):
        self._move_back: Optional[Callable[[], None]] = None
        self._move_next: Optional[Callable[['NavigationNode'], None]] = None

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def process(self):
        raise NotImplementedError

    def move_back(self):
        if self._move_back is not None:
            self._move_back()

    def wait_back(self, callback: Optional[Callable[[], None]] = None):
        choice(
            message='',
            options=[(None, '[Back]')],
        )
        (callback or self.move_back)()

    def start(self, move_next: Callable[['NavigationNode'], None], move_back: Callable[[], None]):
        self._move_next = move_next
        self._move_back = move_back

    def stop(self):
        self._move_back = None
        self._move_next = None


def get_node_name(node: NavigationNode):
    if isinstance(node, FolderNode):
        return '[' + node.get_name().capitalize() + ']'
    return node.get_name().capitalize()


class Navigator:

    def __init__(self):
        super().__init__()
        self._stack: list[NavigationNode] = []
        self._node: Optional[NavigationNode] = None

    def init(self, node: NavigationNode):
        self._set_current_node(node)

    def process(self):
        cls()
        bread_crumbs = [get_node_name(node) for node in self._stack + [self._node]]
        print(' ' + ''.join(bread_crumbs))

        if self._node is not None:
            self._node.process()

    def _set_current_node(self, node: NavigationNode):
        assert node is not None

        if self._node is not None:
            self._node.stop()
            self._stack.append(self._node)

        self._node = node
        node.start(self._set_current_node, self._on_back if self._stack else None)

    def _on_back(self):
        assert self._node is not None
        assert len(self._stack) > 0

        self._node.stop()
        self._node = None
        self._set_current_node(self._stack.pop())


class FolderNode(NavigationNode, ABC):
    CHILDREN: list[NavigationNode] = [
        # filled by inheritors
    ]

    def __init__(self):
        super().__init__()

        self._last_selected: Optional[NavigationNode] = None

    def process(self):
        options: list[tuple[Optional[NavigationNode], str]] = []

        if self._move_back is not None:
            options.append((None, '[...]'))

        options += [
            (node, get_node_name(node)) for node in self.CHILDREN
        ]

        self._last_selected = choice(
            message='',
            options=options,
            default=self._last_selected,
        )

        if self._last_selected is None:
            self.move_back()
            return

        assert isinstance(self._last_selected, NavigationNode)
        assert self._move_next is not None

        self._move_next(self._last_selected)
