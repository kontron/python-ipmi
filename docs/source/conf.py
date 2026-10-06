# Sphinx configuration of the python-ipmi documentation.
#
# Build it locally with:
#   pip install -r docs/requirements.txt -e .
#   sphinx-build -W -b html docs/source docs/_build/html

import os
import sys

# document the package of this source tree, also without installing it
sys.path.insert(0, os.path.abspath('../..'))

import pyipmi  # noqa: E402

project = 'python-ipmi'
copyright = '2019, FerencFarkasPhD'
author = 'FerencFarkasPhD'
release = pyipmi.__version__
version = release

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.graphviz',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

exclude_patterns = []

# the types are taken from the annotations, not from the docstrings
autodoc_typehints = 'description'
autodoc_member_order = 'bysource'
# show the constructor docstring with the class docstring
autoclass_content = 'both'
# list the members without a docstring too, most have none yet
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

html_theme = 'furo'
html_title = f'python-ipmi {release}'
