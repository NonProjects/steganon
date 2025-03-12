from setuptools import setup
from ast import literal_eval

with open('steganon/version.py', encoding='utf-8') as f:
    version = literal_eval(f.read().split('=',1)[1].strip())

setup(
    name             = 'steganon',
    version          = version,
    license          = 'LGPL-2.1',
    description      = 'Steganography LSB Matching (with PRNG by Seed)',
    long_description = open('README.md', encoding='utf-8').read(),
    author           = 'NonProjects',
    author_email     = 'thenonproton@pm.me',
    url              = 'https://github.com/NonProjects/steganon',
    packages         = ['steganon', 'steganon.cli'],
    install_requires = ['pillow'],

    extras_require = {
        'cli': ['click==8.1.7']
    },
    long_description_content_type = 'text/markdown',
    keywords = ['Steganography', 'LSB', 'Cryptography'],

    entry_points='''
        [console_scripts]
        steganon-cli=steganon.cli.steganon_cli:safe_steganon_cli_startup
    ''',

    classifiers = [
        'Intended Audience :: Developers',
        'Topic :: Security :: Cryptography',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)'
    ]
)
