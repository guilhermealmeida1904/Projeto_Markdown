
from abc import ABC, abstractmethod
from typing import Iterable, List

from typing_extensions import override


class MarkdownList(list['ListItem']):
    def __init__(self, iterable: Iterable['ListItem'] = ()):
        super().__init__(iterable)
        self.with_paragraphs = False
    #:

    def add_new_list_item(self, initial_inner_elem: 'ListItemInnerElem') -> 'ListItem':
        curr_list_item = ListItem()
        curr_list_item.append(initial_inner_elem)
        self.append(curr_list_item)
        return curr_list_item
    #:
#:

class ListItem(list['ListItemInnerElem']):
    def add_text_line(self, line: str):
        last_inner_elem = self[-1]

        if isinstance(last_inner_elem, ListItemBlock):
            last_inner_elem.add_line(line)

        elif isinstance(last_inner_elem, ListItemHeading):
            self.append(ListItemBlock(line))

        else:
            assert False, (f'Unknow last item type {type(last_inner_elem)}'
                            f'when adding line: {line}')
    #:
#:

class ListItemInnerElem(ABC):
    @abstractmethod
    def __str__(self) -> str:
        pass

    #:
    def __repr__(self) -> str:
        return f'{type(self).__name__}: {self}'
#:

class ListItemBlock(ListItemInnerElem):
    def __init__(self, initial_line: str):
        self._text_lines = [initial_line]
    #:

    def add_line(self, line: str):
        self._text_lines.append(line)

    @override
    def __str__(self) -> str:
        return '\n'.join(self._text_lines)
#:

class ListItemHeading(ListItemInnerElem):
    def __init__(self, line: str, level: int):
        self._line = line
        self.level = level
    #:

    
    @override
    def __str__(self) -> str:
        return self._line
    #:

#: