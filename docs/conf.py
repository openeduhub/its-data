from its_data._version import __version__

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "data-utils"
copyright = "2024, IT's Jointly"
author = "IT's Jointly"
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_typehints = "both"
autodoc_typehints_format = "short"
autodoc_type_aliases = {
    x: f"its_data.data.{x}"
    for x in [
        "Basic_Value_Not_None",
        "Basic_Value",
        "Terminal_Value",
        "Data_Point",
        "Data_Point_Subtree",
        "Query_Result",
    ]
} | {
    x: f"its_data.filters.{x}"
    for x in [
        "Filter",
        "Predicate",
        "Simple_Predicate",
        "Multi_Value_Predicate",
    ]
}
