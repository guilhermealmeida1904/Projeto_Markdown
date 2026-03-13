
import sys
from textwrap import dedent
from contextlib import closing

from docopt import docopt

from markdown_compiler1 import MarkdownCompiler 
# from markdown_compiler0 import MarkdownCompiler 

from html_backend import HTMLBackend
from utils import from_file_or_stdin, to_file_or_stdout

#############################################################
##
## MAIN DRIVER
##
#############################################################

def main():
    doc = f"""
        Markos is Markdown converter. It converts from Simplified Markdown to HTML.

        Usage:
        {sys.argv[0]} [-s STYLE_SHEET] [-p] [INPUT_FILE] [OUTPUT_FILE]

        Options:
            INPUT_FILE    Markdown source file. Default: stdin
            OUTPUT_FILE   Output source file. Default: stdout
            -h, --help    This help
            -p, --pretty   Prettify HTML output
            -s STYLE_SHEET, --style-sheet=STYLE_SHEET Use this STYLE_SHEET
    """

    args = docopt(dedent(doc))
    style_sheet = args['--style-sheet']
    pretty_print = args['--pretty']

    try:
        in_file = from_file_or_stdin(args['INPUT_FILE'])
        out_file = to_file_or_stdout(args['OUTPUT_FILE'])
        backend = HTMLBackend(out_file, style_sheet, pretty_print)
        
        with in_file, out_file, closing(backend):
            mkd_compiler = MarkdownCompiler(backend)
            mkd_compiler.compile(in_file.read())

    except FileNotFoundError as ex:
        print(f"File not found: {ex.filename}", file = sys.stderr)
        sys.exit(2)

    except PermissionError as ex:
        print(f"Invalid permissions to access file: {ex.filename}", file = sys.stderr)
        sys.exit(13)

    except Exception as ex:
        print(f"An error has occurred:\n{ex.args}\n\n", file = sys.stderr)
        raise ex

#:

if __name__ == '__main__':
    main()
#:
