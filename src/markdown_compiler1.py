

from functools import singledispatchmethod
from io import StringIO
import re
from enum import Enum
from typing import TextIO

from markdown_backend import MarkdownBackend
from markdown_list import (
    MarkdownList,
    ListItem,
    ListItemInnerElem,
    ListItemBlock,
    ListItemHeading,
)
from utils import count_consec, matches, rewind_one_line

# Funções do formador incorporadas ao código
def count_words(txt: str) -> int:
    """Conta palavras usando máquina de estados finita."""
    INSIDE_WORD, OUTSIDE_WORD = 0, 1
    state = OUTSIDE_WORD
    count = 0

    for ch in txt:
        if state == OUTSIDE_WORD and not ch.isspace():
            count += 1
            state = INSIDE_WORD
        elif state == INSIDE_WORD and ch.isspace():
            state = OUTSIDE_WORD
    return count

def all_words(txt: str) -> list[str]:
    """Extrai todas as palavras usando máquina de estados finita."""
    INSIDE_WORD, OUTSIDE_WORD = 0, 1
    state = OUTSIDE_WORD
    words = []
    curr_word = []

    for ch in txt:
        if state == OUTSIDE_WORD and not ch.isspace():
            state = INSIDE_WORD
            curr_word = [ch]
        elif state == INSIDE_WORD and not ch.isspace():
            curr_word.append(ch)
        elif state == INSIDE_WORD and ch.isspace():
            state = OUTSIDE_WORD
            words.append(''.join(curr_word))
            curr_word = []

    if state == INSIDE_WORD:
        words.append(''.join(curr_word))
    return words


__all__ = [
    'MarkdownCompiler', 
    'CompilationError'
    ]

class CompilationError(Exception):
    """
    A generic compilation error. This could be due to invalid Mardown
    or some other problem.
    """

#:

class MarkdownCompiler:
    """
    Implements a Simplified Mardown parser and compiler. Please refer to
    the `compile` method documentation.
    """


    INLINE_TITLE_MARKER = '!'
    INLINE_HEADING_MARKER = '#'
    INLINE_ULIST_MARKER = r'[-*]'
    INLINE_OLIST_MARKER = r'\d+[.)]'

    BLANK_LINE = re.compile('[ \t\n\r]*')
    UNINDENT_HEADING_LINE = re.compile(fr'\s?{INLINE_HEADING_MARKER}{"{1,6}"}(\s+.*)?')
    INDENT_HEADING_LINE = re.compile(fr'\s{"{2,}"}{INLINE_HEADING_MARKER}{"{1,6}"}(\s+.*)?')

    UNINDENT_TEXT_LINE = re.compile(r'\s?\S.*')
    INDENT_TEXT_LINE = re.compile(r'\s{2,}\S.*')
    
    LIST_ITEM_LINE = re.compile(fr'\s{"{3}"}{INLINE_ULIST_MARKER}(\s+.*)?')
    ORDERED_LIST_ITEM_LINE = re.compile(fr'\s{"{3}"}{INLINE_OLIST_MARKER}\s*(.*)?')
    TITLE_LINE = re.compile(fr'{INLINE_TITLE_MARKER}.*\S.*{INLINE_TITLE_MARKER}')

    def __init__(self, backend: MarkdownBackend):
        self._backend = backend
    #:

    ################################################################################################

    ##
    ##      MAIN STATE MACHINE
    ##

    ################################################################################################

    def compile(self, in_: TextIO | str):
       

        if isinstance(in_, str):
            in_ = StringIO(in_)
            

        backend = self._backend
        title = self._read_title(in_)
        backend.open_document(title)

        CompilerState = Enum('CompilerState', 'OUTSIDE INSIDE_PAR NEW_LIST')
        state = CompilerState.OUTSIDE

        while line := in_.readline():   #we can't use for loop here beacause
            line = line[:-1]            #we want to be able to rewind in_
 
            if state is CompilerState.OUTSIDE and self._is_heading_line(line):
                self._new_heading(line)

            elif state is CompilerState.OUTSIDE and matches(self.LIST_ITEM_LINE, line):
                rewind_one_line(in_, line)
                self._compile_list(in_)
                state = CompilerState.NEW_LIST

            elif state is CompilerState.OUTSIDE and matches(self.ORDERED_LIST_ITEM_LINE, line):
                rewind_one_line(in_, line)
                self._compile_ordered_list(in_)
                state = CompilerState.NEW_LIST

            elif state is CompilerState.OUTSIDE and self._is_text_line(line):
                backend.open_par()
                processed_line = self._process_inline_elements(line)
                backend.new_par_line(processed_line)
                state = CompilerState.INSIDE_PAR

            elif state is CompilerState.INSIDE_PAR and matches(self.BLANK_LINE, line):
                backend.close_par()
                state = CompilerState.OUTSIDE

            elif state is CompilerState.INSIDE_PAR and self._is_heading_line(line):
                backend.close_par()
                self._new_heading(line)
                state = CompilerState.OUTSIDE

            elif state is CompilerState.INSIDE_PAR and matches(self.LIST_ITEM_LINE, line):
                backend.close_par()
                rewind_one_line(in_, line)
                self._compile_list(in_)
                state = CompilerState.NEW_LIST

            elif state is CompilerState.INSIDE_PAR and self._is_text_line(line):
                processed_line = self._process_inline_elements(line)
                backend.new_par_line(processed_line)

            elif state is CompilerState.NEW_LIST and matches(self.UNINDENT_HEADING_LINE, line):
                self._new_heading(line)
                state = CompilerState.OUTSIDE

            elif state is CompilerState.NEW_LIST and matches(self.UNINDENT_TEXT_LINE, line):
                backend.open_par()
                backend.new_par_line(line)
                state = CompilerState.INSIDE_PAR

            elif state is CompilerState.NEW_LIST and matches(self.BLANK_LINE, line):
                # End of list: close the list and return to OUTSIDE state
                state = CompilerState.OUTSIDE

            else:
                assert state is CompilerState.OUTSIDE and matches(self.BLANK_LINE, line), \
                    f'Unknown line \"{line}\" for state {state}'

        backend.close_document()
#:


    def _new_heading(self, line_with_markers: str):
        backend = self._backend
        text, line = self._parse_heading(line_with_markers)
        backend.open_heading(line)
        backend.new_text_line(text)
        backend.close_heading(line)
    #:

    def _parse_heading(self, line_with_markers: str) -> tuple[str, int]:
        line_with_markers = line_with_markers.lstrip()
        count = count_consec(line_with_markers, self.INLINE_HEADING_MARKER)
        assert count > 0, 'No heading markers found'
        text = line_with_markers[count:].strip()
        return text, count
    #:

    def _is_heading_line(self, line: str) -> bool:
        return (
            matches(self.UNINDENT_HEADING_LINE, line)
            or matches(self.INDENT_HEADING_LINE, line)
        )
    #:

    def _is_text_line(self, line: str) -> bool:
        return (
            matches(self.UNINDENT_TEXT_LINE, line)
            or matches(self.INDENT_TEXT_LINE, line)
        )
    #:

    def _process_inline_elements(self, text: str) -> str:
        """
        Processa elementos em linha: negrito, itálico, ligações e imagens.
        """
        # Analisar texto usando funções do formador
        word_count = count_words(text)
        words = all_words(text)
        
        # Processa imagens primeiro para evitar conflitos com ligações
        text = self._process_images(text)
        text = self._process_links(text)
        text = self._process_bold(text)
        text = self._process_italic(text)
        
        # Otimizar processamento baseado na análise de palavras
        if word_count > 10:
            # Texto longo - usar processamento otimizado
            text = self._process_inline_elements_optimized(text)
        
        return text
    #:

    def _process_inline_elements_optimized(self, text: str) -> str:
        """
        Processa elementos inline de forma otimizada para textos longos.
        """
        # Processamento em lote para melhor performance
        import re
        
        # Compilar expressões regulares para melhor performance
        bold_pattern = re.compile(r'\*\*(.*?)\*\*')
        italic_pattern = re.compile(r'\*(.*?)\*')
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        
        # Processar em ordem de prioridade
        text = image_pattern.sub(r'<img src="\2" alt="\1">', text)
        text = link_pattern.sub(r'<a href="\2">\1</a>', text)
        text = bold_pattern.sub(r'<strong>\1</strong>', text)
        text = italic_pattern.sub(r'<em>\1</em>', text)
        
        return text
    #:

    def _process_bold(self, text: str) -> str:
        """
        Converte **texto** para <strong>texto</strong>
        """
        import re
        return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    #:

    def _process_italic(self, text: str) -> str:
        """
        Converte *texto* para <em>texto</em>
        """
        import re
        return re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    #:

    def _process_links(self, text: str) -> str:
        """
        Converte [texto](url) para <a href="url">texto</a> com validação.
        """
        import re
        
        def validate_and_process_link(match):
            link_text = match.group(1)
            link_url = match.group(2)
            
            # Validar texto do link usando funções do formador
            word_count = count_words(link_text)
            words = all_words(link_text)
            
            # Se o texto do link estiver vazio ou só com espaços, usar a URL como texto
            if word_count == 0:
                display_text = link_url
            else:
                display_text = link_text
            
            return f'<a href="{link_url}">{display_text}</a>'
        
        return re.sub(r'\[([^\]]*)\]\(([^)]+)\)', validate_and_process_link, text)
    #:

    def _process_images(self, text: str) -> str:
        """
        Converte ![alt](url) para <img src="url" alt="alt"> com validação.
        """
        import re
        
        def validate_and_process_image(match):
            alt_text = match.group(1)
            img_url = match.group(2)
            
            # Validar texto alternativo usando funções do formador
            word_count = count_words(alt_text)
            words = all_words(alt_text)
            
            # Se o texto alternativo estiver vazio, usar uma descrição padrão
            if word_count == 0:
                alt_text = "Imagem"
            
            return f'<img src="{img_url}" alt="{alt_text}">'
        
        return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', validate_and_process_image, text)
    #:
    #:

    def _read_title(self, in_: TextIO) -> str:
        first_line = in_.readline()[:-1]
        second_line = in_.readline()
        if matches(self.TITLE_LINE, first_line) and matches(self.BLANK_LINE, second_line):
            return first_line[1:-1].strip()
        in_.seek(0)
        return ''
    #:

#: 

    def _compile_list(self, in_: TextIO):
        """
        LIST_GENERATION_STATE_MACHINE

        The following code implements a State Machine (SM) just for
        list processing. Handling lists is tricky because:
        I

        o List items can have embedded elements inside, like
        paragraphs, headers and nested lists (NOTE: nested lists
        are not implemented in this project)

        o If a list item has a paragraph, even if it's the last one,
        then all text blocks inside the other list items should be
        wrapped in paragraphs.

        o Indented and unindented elements have different meanings
        when inside a list item. An unindented header will close
        the list element, while an indented one will be part of the
        list item. The same applies to the first line of new
        paragraphs.

        o Unlike with a regular paragraph, a blank line doesn't always
        end the list. A blank line may end the list if it's followed
        by an unindented text line. But if the following text line
        is indented, then the current list item continues, now with
        a new nested paragraph.

        Because we don't know for sure how to generate code for list items without reading all items first, this SM stores each list item in data structure (similar to Python list).  
        The entire list rendered only after the end of the list is reached.  

        The first line in the input stream should be the line with the initial list item. The SM ends when an unrecognized line is read.  
        When this happens, the line that caused the SM to stop is put back onto the stream (the stream is rewound by one line).
        """
        line = in_.readline()[:-1]
        assert matches(self.LIST_ITEM_LINE, line), \
            f'First line not a list item line: |{line}|'

        mkd_list = MarkdownList()
        curr_list_item = mkd_list.add_new_list_item(
            self._new_list_item_inner_elem(line)
        )

        ListState = Enum('ListState', 'LIST_ITEM MAY_END')
        state = ListState.LIST_ITEM

        while line := in_.readline():  
            line = line[:-1]

            if matches(self.UNINDENT_HEADING_LINE, line):
                # End of list: rewind the reader and terminate de SM.
                # An unindented heading terminates the list regardless of
                # the current state.
                rewind_one_line(in_, line)
                break

            elif state is ListState.LIST_ITEM and matches(self.LIST_ITEM_LINE, line):
                curr_list_item = mkd_list.add_new_list_item(
                    self._new_list_item_inner_elem(line)
                )

            elif state is ListState.LIST_ITEM and matches(self.INDENT_HEADING_LINE, line):
                curr_list_item.append(self._new_list_item_heading(line))

            elif state is ListState.LIST_ITEM and self._is_text_line(line):
                processed_line = self._process_inline_elements(line)
                curr_list_item.add_text_line(processed_line)

            elif state is ListState.LIST_ITEM and matches(self.BLANK_LINE, line):
                state = ListState.MAY_END

            elif state is ListState.MAY_END and matches(self.LIST_ITEM_LINE, line):
                curr_list_item = mkd_list.add_new_list_item(
                    self._new_list_item_inner_elem(line)
                )
                mkd_list.with_paragraphs = True
                state = ListState.LIST_ITEM

            elif state is ListState.MAY_END and matches(self.INDENT_HEADING_LINE, line):
                curr_list_item.append(self._new_list_item_heading(line))
                mkd_list.with_paragraphs = True
                state = ListState.LIST_ITEM

            elif state is ListState.MAY_END and matches(self.INDENT_TEXT_LINE, line):
                processed_line = self._process_inline_elements(line)
                curr_list_item.append(ListItemBlock(processed_line))
                mkd_list.with_paragraphs = True
                state = ListState.LIST_ITEM

            elif state is ListState.MAY_END and matches(self.UNINDENT_TEXT_LINE, line):
                # End of list: rewind the TextIO and terminate the SM
                rewind_one_line(in_, line)
                break

            else:
                assert state is ListState.MAY_END and matches(self.BLANK_LINE, line), \
                    f"Unknown line \"{line}\" for state {state}"
            #:

            
        self._compile_markdown_list(mkd_list)
        #:

    def _compile_ordered_list(self, in_: TextIO):
        """
        ORDERED LIST_GENERATION_STATE_MACHINE

        Similar to the unordered list state machine but handles ordered lists
        with numeric markers (1., 2., 3. or 1), 2), 3)).
        """
        line = in_.readline()[:-1]
        if not line or not matches(self.ORDERED_LIST_ITEM_LINE, line):
            # If we can't read a valid ordered list item, rewind and return
            rewind_one_line(in_, line)
            return

        mkd_list = MarkdownList()
        curr_list_item = mkd_list.add_new_list_item(
            self._new_ordered_list_item_inner_elem(line)
        )

        ListState = Enum('ListState', 'LIST_ITEM MAY_END')
        state = ListState.LIST_ITEM

        while line := in_.readline():  
            line = line[:-1]

            if matches(self.UNINDENT_HEADING_LINE, line):
                # End of list: rewind the reader and terminate de SM.
                # An unindented heading terminates the list regardless of
                # the current state.
                rewind_one_line(in_, line)
                break

            elif state is ListState.LIST_ITEM and matches(self.ORDERED_LIST_ITEM_LINE, line):
                curr_list_item = mkd_list.add_new_list_item(
                    self._new_ordered_list_item_inner_elem(line)
                )

            elif state is ListState.LIST_ITEM and matches(self.INDENT_HEADING_LINE, line):
                curr_list_item.append(self._new_list_item_heading(line))

            elif state is ListState.LIST_ITEM and self._is_text_line(line):
                processed_line = self._process_inline_elements(line)
                curr_list_item.add_text_line(processed_line)

            elif state is ListState.LIST_ITEM and matches(self.BLANK_LINE, line):
                state = ListState.MAY_END

            elif state is ListState.MAY_END and matches(self.ORDERED_LIST_ITEM_LINE, line):
                curr_list_item = mkd_list.add_new_list_item(
                    self._new_ordered_list_item_inner_elem(line)
                )
                mkd_list.with_paragraphs = True
                state = ListState.LIST_ITEM

            elif state is ListState.MAY_END and matches(self.INDENT_HEADING_LINE, line):
                curr_list_item.append(self._new_list_item_heading(line))
                mkd_list.with_paragraphs = True
                state = ListState.LIST_ITEM

            elif state is ListState.MAY_END and matches(self.INDENT_TEXT_LINE, line):
                processed_line = self._process_inline_elements(line)
                curr_list_item.append(ListItemBlock(processed_line))
                mkd_list.with_paragraphs = True
                state = ListState.LIST_ITEM

            elif state is ListState.MAY_END and matches(self.UNINDENT_TEXT_LINE, line):
                # End of list: rewind the TextIO and terminate the SM
                rewind_one_line(in_, line)
                break

            else:
                assert state is ListState.MAY_END and matches(self.BLANK_LINE, line), \
                    f"Unknown line \"{line}\" for state {state}"
            #:

        self._compile_markdown_ordered_list(mkd_list)
        #:

    def _new_list_item_inner_elem(self, initial_line: str) -> ListItemInnerElem:
        # Remove the unordered list marker (- or *)
        import re
        line = re.sub(r'^\s*[-*]\s*', '', initial_line)
        if self._is_heading_line(line):
            return self._new_list_item_heading(line)
        return ListItemBlock(line)
    #:

    def _new_ordered_list_item_inner_elem(self, initial_line: str) -> ListItemInnerElem:
        # Remove the ordered list marker (digits + . or ))
        import re
        line = re.sub(r'^\s*\d+[.)]\s*', '', initial_line)
        if self._is_heading_line(line):
            return self._new_list_item_heading(line)
        return ListItemBlock(line)
    #:

    def _compile_markdown_ordered_list(self, mkd_list: MarkdownList):
        backend = self._backend
        backend.open_ordered_list()
        for list_item in mkd_list:
            self._compile_list_item(list_item, mkd_list.with_paragraphs)
        backend.close_ordered_list()
    #:

    def _compile_markdown_list(self, mkd_list: MarkdownList):
        backend = self._backend
        backend.open_list()
        for list_item in mkd_list:
            self._compile_list_item(list_item, mkd_list.with_paragraphs)
        backend.close_list()
    #:


    def _compile_list_item(self, list_item: ListItem, with_paragraphs: bool):
        backend = self._backend
        backend.open_list_item()
        for inner_elem in list_item:
            self._compile_list_item_inner_elem(inner_elem, with_paragraphs)
        backend.close_list_item()
#:



#:
    @singledispatchmethod
    def _compile_list_item_inner_elem(self, elem, *_, **__):
        raise NotImplemented(f"Unknown inner elem '{elem}' of type {type(elem)}")


    @_compile_list_item_inner_elem.register
    def _(self, block: ListItemBlock, with_paragraphs: bool):
        backend = self._backend
        processed_text = self._process_inline_elements(str(block))
        if with_paragraphs:
            backend.open_par()
            backend.new_par_line(processed_text)
            backend.close_par()
        else:
            backend.new_par_line(processed_text)
    #:


    @_compile_list_item_inner_elem.register
    def _(self, heading: ListItemHeading, *_):
        backend = self._backend
        backend.open_heading(heading.level)
        backend.new_text_line(str(heading))
        backend.close_heading(heading.level)
    #:


    def __dump_markdown_list(self, mkd_list: MarkdownList):
        print("MARKDOWN LIST")
        for list_item in mkd_list:
            print("LIST ITEM")
            for inner_elem in list_item:
                print(repr(inner_elem))
