from setuptools import setup

setup(
    name             = 'steganon',
    version          = '0.1',
    license          = 'LGPL-2.1',
    description      = 'Steganography LSB (with PRNG by seed)',
    long_description = open('README.md', encoding='utf-8').read(),
    author           = 'NonProjects',
    author_email     = 'thenonproton@pm.me',
    url              = 'https://github.com/NonProjects/steganon',
    packages         = ['steganon'],
    install_requires = ['pillow'],

    long_description_content_type = 'text/markdown',
    keywords = ['Steganography', 'LSB', 'Cryptography'],

    classifiers = [
        'Intended Audience :: Developers',
        'Topic :: Security :: Cryptography',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)'
    ]
)
