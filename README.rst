========================================================================
sphinx-mekki
========================================================================

A `Sphinx <https://www.sphinx-doc.org>`_ extension to embed images, download files, CSSs, and JSs into a single HTML file.

Installation
========================================================================

You are able to install ``sphinx-mekki`` with ``pip``.

.. code-block:: shell

   pip install sphinx-mekki

Usage
========================================================================

You must add ``sphinx_mekki`` to your extensions list in your ``conf.py``.

.. code-block:: python

   extensions = [... , "sphinx_mekki", ...]

You are optionally able to change the html_theme to ``mekki`` in the ``conf.py`` to generate simple HTML files with minimal dependency on other pages. (Hopefully, this extension should work with any HTML theme that complies with Sphinx.)

.. code-block:: python

   html_theme = "mekki"

Enjoy writing docs!
