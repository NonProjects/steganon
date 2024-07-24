"""This module contains tools for CLI"""

from click import echo, style

def progress_callback(current: int, total: int):
    text = style(text=f'@ Working on data... {int(current/total*100)}%\r',
                 fg='white', bold=True)
    echo(text, nl=False)
