"""
Setup script for creating a Mac .app bundle using py2app
Run: python setup.py py2app
"""

from setuptools import setup

APP = ['bib_gui_modern.py']
DATA_FILES = ['test_data']
OPTIONS = {
    'py2app': {
        'argv_emulation': False,
        'packages': ['bibtexparser', 'thefuzz', 'customtkinter'],
        'includes': ['bibtexparser.bparser', 'bibtexparser.bwriter'],
        'excludes': ['matplotlib', 'numpy', 'pandas'],  # Reduce app size
        'resources': DATA_FILES,
        'strip': True,
        'use_pythonframework': True,
    }
}

setup(
    name='BibTeX Manager',
    app=APP,
    data_files=DATA_FILES,
    options=OPTIONS,
    setup_requires=['py2app'],
    version='1.0.0',
    description='BibTeX Bibliography Manager for deduplicating and organizing bibliography files',
    author='Thomas',
    url='https://github.com/yourusername/bibtex-manager',
)
