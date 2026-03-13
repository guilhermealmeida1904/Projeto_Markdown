
from abc import ABC, abstractmethod


# ABC => Abstract Base Class (Interface)

class MarkdownBackend(ABC):
    @abstractmethod
    def open_document(self, title = ''):
        pass

    @abstractmethod
    def close_document(self):
        pass

    @abstractmethod
    def open_heading(self, level: int):
        pass
    #:

    @abstractmethod
    def close_heading(self, level: int):
        pass
    #:

    @abstractmethod
    def new_text_line(self, line: str):
        pass
    #:

    @abstractmethod
    def open_par(self):
        pass

    #:
    @abstractmethod
    def close_par(self):
        pass
    #:
    
    @abstractmethod
    def new_par_line(self, line: str):
        pass
    #:


    @abstractmethod
    def open_list(self):
        pass
    #:


    @abstractmethod
    def close_list(self):
        pass
    #:

    @abstractmethod
    def open_list_item(self):
        pass
    #:


    @abstractmethod
    def close_list_item(self):
        pass
    #:

    @abstractmethod
    def open_ordered_list(self):
        pass
    #:

    @abstractmethod
    def close_ordered_list(self):
        pass
    #:

