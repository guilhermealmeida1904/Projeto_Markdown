
from typing import TextIO
from io import StringIO
from typing_extensions import override # for Python < 3.12

from markdown_backend import MarkdownBackend
from utils import prettify_html

class HTMLBackend(MarkdownBackend):
    def __init__(self, out: TextIO, style_sheet = '', pretty_print = False):
        self._storage = out
        self._out = StringIO()
        self._style_sheet = style_sheet
        self._pretty_print = pretty_print
    #:


    def close(self):
        self._storage.write(
            prettify_html(self._out.getvalue()) if self._pretty_print else
            self._out.getvalue()
        )
        self._out.close()
    #:
   

    @override
    def open_document(self, title=''):
        out = self._out
        out.write("""<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """ .replace('\n', ''))
        
        if title:
            out.write(f'<title>{title}</title>')
        if self._style_sheet:
            out.write('<link rel="stylesheet" media="all" type="text/css" '
                    + f'href="{self._style_sheet}"')
        out.write('</head><body>')
    #:


    @override
    def close_document(self):
        self._out.write('</body></html>')
    #:

    @override
    def open_heading(self, line: str):
        self._out.write(f'<h{line}>')
    #:

    @override
    def close_heading(self, line: str):
        self._out.write(f'</h{line}>')
    #:

    @override
    def new_text_line(self, line: str):
        self._out.write(line)
    #:

    @override
    def open_par(self):
        self._out.write(f'<p>')
    #:

    @override
    def close_par(self):
        self._out.write('</p>')
    #:

    @override
    def new_par_line(self, line: str):
        self._out.write(f' {line}')
    #:

    @override
    def open_list(self):
        self._out.write(f'<ul>')
    #:


    @override
    def close_list(self):
        self._out.write(f'</ul>')
    #:

    @override
    def open_list_item(self):
        self._out.write(f'<li>')

    #:


    @override
    def close_list_item(self):
        self._out.write(f'</li>')

    #:

    @override
    def open_ordered_list(self):
        self._out.write(f'<ol>')

    #:

    @override
    def close_ordered_list(self):
        self._out.write(f'</ol>')

    #:

#:
    
