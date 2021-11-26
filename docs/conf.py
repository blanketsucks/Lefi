import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "Lefi"
copyright = "2021, Andy"
author = "Andy"

release = "0.2.3a"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.extlinks",
]

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_class_signature = "separated"
add_module_names = True

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

templates_path = ["_templates"]
html_static_path = ["_static"]
html_theme = "furo"
html_theme_options = {
    "navigation_with_keys": True,
    "announcement": "<a href='https://discord.com/invite/QPFXzFbqrK'>Join the discord!</a>",
}

pygments_style = "native"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "aiohttp": ("https://docs.aiohttp.org/en/latest/", None),
}
