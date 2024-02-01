#!/usr/bin/env python3

from os import getenv
from pathlib import Path

from traceback import format_exception
from sys import stdout, version as sys_version

try:
    import click
except ImportError:
    raise RuntimeError(
        'SteganoN was installed without CLI. Try to install steganon[cli]'
    )
from steganon import LSB_WS, Image, pngify, VERSION

# ========================================================= #
# = CLI configuration ===================================== #

class StructuredGroup(click.Group):
    def __init__(self, name=None, commands=None, **kwargs):
        super().__init__(name, commands, **kwargs)
        self.commands = commands or {}

    def list_commands(self, ctx):
        return self.commands

    def format_commands(self, ctx, formatter):
        formatter.write_text('')
        formatter.write_heading('Commands')

        for k,v in self.commands.items():
            if v.hidden:
                continue

            if v.name == 'info':
                command_name = click.style(v.name, fg='cyan', bold=True)
            else:
                command_name = click.style(v.name, fg='white', bold=True)

            text = f'  o  {command_name} :: {v.get_short_help_str().strip()}'
            formatter.write_text(text)

        formatter.write_text('\x1b[0m')

@click.group(cls=StructuredGroup)
def cli():
    pass

# ========================================== #
# = CLI commands =========================== #

@cli.command()
@click.option(
    '--data', '-d', required=True, prompt=True,
    help='Secret data to hide in image. Can be File, Hex or Text.'
)
@click.option(
    '--seed', '-s', required=True, prompt=True,
    help='''Unique seed to shuffle target pixels.
            Keep it secret. Can be File, Hex or Text.'''
)
@click.option(
    '--input', '-i', required=True, prompt=True,
    type=click.Path(readable=True, exists=True),

    help='''Target Image file in which pixels we
            will write your secret --data'''
)
@click.option(
    '--output', '-o',
    help='''A file to which we will write
            Image bytes with your secret --data.
            If not specified, will write to
            --target. If "STDOUT" specified,
            will write to your STDOUT.'''
)
@click.option(
    '--testmode', is_flag=True,
    help='Will enable TestMode'
)
def hide(data, seed, input, output, testmode):
    """
    Command to hide Data inside pixels of Image

    \b
    Example:\b
        steganon-cli hide --input image.png --data "My secret data"\\
            --seed "VerySecretSeed" --output image_hidden.png
        \b
        steganon-cli hide --input image.png --data secret.txt\\
            --seed seed.txt --output STDOUT
        \b
        ?: Ignore --output option to write back to --input.
    """
    if Path(data).exists():
        data = open(data, 'rb').read()
    else:
        try:
            data = int(data, 16)
        except ValueError:
            data = data.encode()

    if Path(seed).exists():
        seed = open(seed, 'rb').read()
    else:
        try:
            seed = int(seed, 16)
        except ValueError:
            seed = seed.encode()

    lsb_ws = LSB_WS(Image.open(input), seed,
                    testmode=testmode)
    lsb_ws.hide(data)

    if not output:
        output = input

    elif output == 'STDOUT':
        output = stdout.buffer

    lsb_ws.save(output, format='PNG')

@cli.command()
@click.option(
    '--seed', '-s', required=True, prompt=True,
    help='''Seed to extract target pixels.
            Can be File, Hex or Text.'''
)
@click.option(
    '--input', '-i', required=True, prompt=True,
    type=click.Path(readable=True, exists=True),

    help='''Target Image from which pixels we
            will extract your Secret Data'''
)
@click.option(
    '--output', '-o',
    help='''A file to which we will write your
            extracted Secret Data. If not
            specified, will write to STDOUT'''
)
def extract(seed, input, output):
    """
    Command to get Data from pixels of Image

    \b
    Example:\b
        steganon-cli extract --input image_hidden.png --seed "VerySecretSeed"
        \b
        steganon-cli extract --input image_hidden.png --seed "VerySecretSeed"\\
            --output secret.txt
    """
    if Path(seed).exists():
        seed = open(seed, 'rb').read()
    else:
        try:
            seed = int(seed, 16)
        except ValueError:
            seed = seed.encode()

    lsb_ws = LSB_WS(Image.open(input), seed)
    secret_data = lsb_ws.extract()

    if output:
        out = open(output, 'wb')
    else:
        out = stdout.buffer

    out.write(secret_data)

@cli.command(name='pngify')
@click.option(
    '--input', '-i', required=True, prompt=True,
    type=click.Path(readable=True, exists=True),
    help='Target Image to convert to PNG'
)
@click.option(
    '--output', '-o', required=True, prompt=True,
    help='''A file to which we will save converted to PNG
            --input file. Can be "STDOUT"'''
)
def _pngify(input, output):
    """
    Command to convert any Image file to PNG

    \b
    Example:\b
        steganon-cli pngify --input image.jpg --output image.png
    """
    output = stdout.buffer if output == 'STDOUT' else output
    pngify(Image.open(input)).save(output, format='PNG')

@cli.command()
def info():
    """Command to retrieve basic info about App"""

    python_version = click.style(sys_version.split()[0], fg='white', bold=True)
    steganon_version = click.style(VERSION, fg='white', bold=True)
    author = click.style('NotStatilko', fg='white', bold=True)
    github = click.style('github.com/NonProjects/steganon', fg='blue', bold=True)
    license = click.style('LGPL-2.1 (NonProjects)\n', fg='white', bold=True)

    if getenv('BLACK_SABBATH'):
        black_sabbath = """
    Rocket engines burning fuel so fast
    Up into the night sky they blast
    Through the universe the engines whine
    Could it be the end of man and time?

    Back on earth the flame of life burns low
    Everywhere is misery and woe
    Pollution kills the air, the land and sea
    Man prepares to meet his destiny, yeah
    """
        black_sabbath = click.style(
            black_sabbath, fg='black', bg='white', bold=True, italic=True)
    else:
        black_sabbath = ''

    click.secho(
        f'''python_version={python_version}, steganon_version={steganon_version}, '''
        f'''author={author}, github={github}, license={license}{black_sabbath}'''
    )

def safe_steganon_cli_startup():
    try:
        cli(standalone_mode=False)
    except Exception as e:
        if isinstance(e, click.Abort):
            click.echo(); exit(0)

        traceback = ''.join(format_exception(
            e,
            value = e,
            tb = e.__traceback__
        ))
        if getenv('STEGANON_CLI_DEBUG'):
            click.secho(traceback, fg='red')

        elif e.args: # Will echo only if error have message
            click.secho(e, fg='red')

        exit(1)

if __name__ == '__main__':
    safe_steganon_cli_startup()
