========================================================================
sphinx-mekki
========================================================================

A `sphinx <https://www.sphinx-doc.org>`_ extension to embed images/downloads/CSSs/JSs to single HTML file.

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

You are optionally able to change the html_theme to ``mekki`` in your ``conf.py`` to generate simple HTML files. (Hopefully any HTML theme should work with this extension.)

.. code-block:: python

   html_theme = "mekki"

Enjoy writing docs!
