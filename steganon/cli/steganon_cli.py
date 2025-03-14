#!/usr/bin/env python3

from os import getenv
from pathlib import Path
from io import BytesIO

from traceback import format_exception
from sys import stdout, version as sys_version
from code import interact as interactive_console
try:
    import click
except ImportError:
    raise RuntimeError(
        'SteganoN was installed without CLI. Try to install steganon[cli]'
    )
from steganon import LSB_MWS, Image, VERSION, pngify as pngify_
from .tools import progress_callback


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

        for v in self.commands.values():
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
    '--format', '-f',
    help='''--output image file format. E.g TIFF, JPEG2000,
            WEBP, etc. Should be specified if you Hide from
            one format (e.g PNG) to another (e.g WEBP)'''
)
@click.option(
    '--silent', is_flag=True,
    help='''Will not report progress if specified'''
)
@click.option(
    '--testmode', is_flag=True,
    help='Will enable TestMode. R=0,G=1,B=2,Y=3 bits changed per pixel'
)
@click.option(
    '--use-raw-seed', is_flag=True,
    help='If specified, will not hash seed(s). Not recommended!'
)
def hide(data, seed, input, output, format, silent, testmode, use_raw_seed):
    """
    Hide your data inside Image pixels

    \b
    Tested formats: PNG, BMP, TIFF, WEBP & JP2. SteganoN
    does NOT support JPEG and other lossy formats.
    \b
    You can hide multiple data on different Seeds in one
    --input Image. In future, to extract first data you
    will need to enter first Seed, to extract second
    data you will need to enter first AND second, and
    so on. There is virtually no limit on how many
    Seeds in row you can use, except obvious Image
    pixels size limit (~three pixels per byte).
    \b
    By using multiple seeds we can implement Deniable
    steganography hide. In a case of extortion You
    can provide only one (or even two, if your actual
    secret data is three seeds deep.) Seed. Attacker
    will never know how deep your hide goes. Maybe
    it's only one at all?
    \b
    You should NEVER keep original --input image
    near the one that was processed with SteganoN,
    otherwise it's possible to compare them and
    find modified pixels. Though without Seed
    they are useless, You can be forced to tell
    secret Seed. Here Deniable Hide is useful,
    but not as much because not all modified
    pixels will be touched on first seed.
    \b
    The standart usage is pretty simple:\b
        steganon-cli hide --input image.png --data "My secret data"\\
            --seed "VerySecretSeed" --output image_hidden.png
        \b
        steganon-cli hide --input image.png --data secret.txt\\
            --seed seed.txt --output STDOUT
        \b
        steganon-cli hide --input image.png --data secret.txt\\
            --seed seed.txt --output image_hidden.webp --format WEBP
    \b
    ?: Skip --output flag if you want to write back to --input.
    !: You can specify --data and --seed as HEX, use 0x prefix:
    V
    steganon-cli hide --input image.png --data 0x5374617267617a6572\\
        --seed 0x5261696e626f77 --output image_hidden.webp --format WEBP
    \b
    To write Deniable hide You should use a special format:\b
        steganon-cli hide -i image.png -d "Wow very secret! | Actual secret"\\
            -s "VerySecretSeed | RealSecretSeed" -o image_hidden.png
    \b
    As you can see, here we use a "|" symbol to split Datas/
    Seeds. This format support same things as default one:
    you can specify seed/data as Hexadecimal or as a file:\b
        steganon-cli hide -i image.png -d "0x576f7720766572792073656372657421 | Actual secret"\\
            -s "seed.txt | 0x5265616c53656372657453656564" -o image_hidden.png
    \b
    (!)
    You are recommended to additionally use "exiftool"
    program to mirror *all* metadata from original
    Image to Hidden if it's installed on your system.
    \b
    exiftool -TagsFromFile original.png -all:all\\
        -overwrite_original hidden.png
    """
    progress_c = progress_callback if not silent else None

    data, data_p = data.split(' | '), []
    if len(data) == 1: # We want to ignore whitespace and also account for
        data = data[0].split('|') # situations where used specified e.g
                                  # --data "DATA0|DATA1" (not "DATA0 | DATA1")
    seed, seed_p = seed.split(' | '), []
    if len(seed) == 1: # We want to ignore whitespace and also account for
        seed = seed[0].split('|') # situations where used specified e.g
                                  # --seed "SEED0|SEED1" (not "SEED0 | SEED1")
    if len(data) != len(seed):
        click.secho(
            f'You provided {len(data)} datas but {len(seed)} '
            'seeds. Mismatch! Check --help for usage.', fg='red')
        return

    for d in data:
        if Path(d).exists():
            d = open(d,'rb').read()
        else:
            if d.startswith('0x'):
                d = bytes.fromhex(d[2:])
            else:
                d = d.encode()
        data_p.append(d)

    for s in seed:
        if Path(s).exists():
            s = open(s,'rb').read()
        else:
            if s.startswith('0x'):
                s = bytes.fromhex(s[2:])
            else:
                s = s.encode()
        seed_p.append(s)

    lsb_mws = LSB_MWS(Image.open(input), seed_p, testmode=testmode,
        progress_callback=progress_c, use_raw_seed=use_raw_seed)

    while data_p:
        lsb_mws.hide(data_p.pop(0))
        if data_p:
            lsb_mws.next()

    if not output:
        output = input

    elif output == 'STDOUT':
        output = stdout.buffer

    lsb_mws.save(output, format=format)
    click.echo('')

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
@click.option(
    '--chunksize', '-c', type=int,
    help='''Amount of bytes written per one iteration.
            Please note that RAM consumption will be
            much higher than chunksize. Default is
            250KB or 250000, which corresponds to
            about 270MB of RAM. Typically bigger
            chunksize doesn't impact speed much'''
)
@click.option(
    '--infosize', is_flag=True,
    help='''If specified, will only echo Information
    Size on last given --seed. If --out specified,
    will write raw integer into the file.'''
)
@click.option(
    '--silent', is_flag=True,
    help='''Will not report progress if specified'''
)
def extract(seed, input, output, chunksize, infosize, silent):
    """
    Extract hidden data from Image pixels

    \b
    Example with one Seed:\b
        steganon-cli extract --input image_hidden.png --seed "VerySecretSeed"
        \b
        steganon-cli extract --input image_hidden.png --seed "VerySecretSeed"\\
            --output secret.txt
        \b
        !: You can specify --data and --seed as HEX, use 0x prefix:
        V
        steganon-cli extract --input image_hidden.png --seed 0x5261696e626f77
    \b
    Multiseed example:\b
        steganon-cli extract -i image_hidden.png -s\\
            "VerySecretSeed | RealSecretSeed" -o "secret.txt | actual_secret.txt"
    \b
    You can specify "_" as output to ignore data. This can be useful
    on Multiseed (if you want only to obtain deeper data), e.g:\b
        steganon-cli extract -i image_hidden.png -s\\
            "VerySecretSeed | RealSecretSeed" -o "_ | actual_secret.txt"
    \b
    ?: Check --help on "hide" command for more details on Deniable
       Hide & Multiseed usage. Extract supports all formatting
       from the "hide", e.g Hexadecimal and file.
    """
    progress_c = None if silent else progress_callback

    seed, seed_p = seed.split(' | '), []
    if len(seed) == 1: # We want to ignore whitespace and also account for
        seed = seed[0].split('|') # situations where user specified e.g
                                  # --seed "SEED0|SEED1" (not "SEED0 | SEED1")
    output = (output or '').split('|')
    output = [o.strip() for o in output if o]
    output.extend(['_STDOUT']*(len(seed) - len(output)))

    for s in seed:
        if Path(s).exists():
            s = open(s,'rb').read().strip()
        else:
            if s.startswith('0x'):
                s = bytes.fromhex(s[2:])
            else:
                s = s.encode().strip()
        seed_p.append(s)

    lsb_mws = LSB_MWS(Image.open(input), seed_p,
        progress_callback=progress_c)

    for i,_ in enumerate(seed_p):
        if infosize and i+1 < len(seed_p):
            out = None

        elif infosize and output[i] in ('_STDOUT', '_'):
            out = None; break

        elif infosize and output[i] in ('STDOUT', '_STDOUT'):
            out = stdout.buffer; break

        elif output[i] in ('STDOUT', '_STDOUT'):
            out = stdout.buffer
        elif output[i] == '_':
            out = None
        else:
            out = open(output[i], 'wb')

        secret_data_gen = lsb_mws.extractgen(chunksize)
        for block in secret_data_gen:
            if out and not infosize:
                out.write(block)

        if i+1 == len(seed_p):
            break
        lsb_mws.next()

    if infosize and out:
        out.write(str(lsb_mws.extract_infosize()).encode())

    if infosize and not out:
        power, n = 10**3, 0
        power_labels = {0 : '', 1: 'K', 2: 'M'}
        isize = lsb_mws.extract_infosize()

        while isize > power:
            isize /= power
            n += 1

        isize = f'{round(isize,1)}{power_labels[n]}B'

        s = click.style('@ Size of embedded Info on Image:', fg='white', bold=True)
        m = click.style(isize, fg='yellow', bold=True)
        click.echo(f'{s} {m}({lsb_mws.extract_infosize()})')

    click.echo('')

@cli.command()
@click.option(
    '--input', '-i', required=True, prompt=True,
    type=click.Path(readable=True, exists=True),
    help='''Target Image file which capacity you wish to get'''
)
@click.option(
    '--raw', is_flag=True, help='Return only integer'
)
def capacity(input, raw):
    """
    Get embedding capacity of selected Image

    \b
    Example:\b
        steganon-cli capacity --input image.png
        steganon-cli capacity --raw --input image.png
    """
    lsb_mws = LSB_MWS(Image.open(input), b'')
    capacity = lsb_mws.max_allowed_bytes

    if raw:
        click.echo(capacity)
        return

    power, n = 10**3, 0
    power_labels = {0 : '', 1: 'K', 2: 'M'}

    while capacity > power:
        capacity /= power
        n += 1

    capacity = f'{round(capacity,1)}{power_labels[n]}B'

    s = click.style('@ Max embedding capacity of this Image:', fg='white', bold=True)
    m = click.style(capacity, fg='yellow', bold=True)
    click.echo(f'{s} {m}({lsb_mws.max_allowed_bytes})\n')

@cli.command()
@click.option(
    '--input', '-i', required=True, prompt=True,
    type=click.Path(readable=True, exists=True),
    help='Target Image to convert to PNG/lossless format'
)
@click.option(
    '--format', '-f', default='PNG',
    help='Format of --output Image. Default is PNG.'
)
@click.option(
    '--output', '-o', required=True, prompt=True,
    help='''A file to which we will save converted to PNG
            --input file. Can be "STDOUT"'''
)
def pngify(input, format, output):
    """
    Convert any Image to PNG/lossless format

    \b
    Example:\b
        steganon-cli pngify --input image.jpg --output image.png
        steganon-cli pngify --input image.jpg --output image.tiff --format TIFF
    \b
    (!)
    You are recommended to additionally use "exiftool"
    program to mirror *all* metadata from original
    Image to Out if it's installed on your system.
    \b
    exiftool -TagsFromFile input.png -all:all\\
        -overwrite_original output.png

    """
    output = BytesIO() if output == 'STDOUT' else output
    try:
        prcsdi = pngify_(Image.open(input), format=format)
    except KeyError as e:
        raise KeyError(f'Invalid --format: {format}') from e
    prcsdi.save(output, format=format)

    if isinstance(output, BytesIO):
        output.seek(0,0)
        stdout.buffer.write(output.read())

@cli.command()
def info():
    """Get information about this SteganoN build"""

    python_version = click.style(sys_version.split()[0], fg='white', bold=True)
    steganon_version = click.style(VERSION, fg='white', bold=True)
    author = click.style('NotStatilko', fg='white', bold=True)
    github = click.style('github.com/NonProjects/steganon', fg='blue', bold=True)
    license = click.style('LGPL-2.1(NonProjects)\n', fg='white', bold=True)

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

@cli.command(hidden=True)
def python():
    """Launch interactive Python console"""
    interactive_console(local=globals())

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
