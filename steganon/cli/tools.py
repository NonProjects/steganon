"""This module contains tools for CLI"""

from click import echo, style

def progress_callback(current: int, total: int, seed_indx: int):
    text = style(
        text=f'@ Working on data[{seed_indx+1}]... {int(current/total*100)}%  \r',
        fg='green' if current >= total else 'yellow')
    echo(text, nl=False)
