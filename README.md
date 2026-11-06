# MPC Manual to Web

A Python pipeline that converts the Akai MPC user guide from a single PDF into a
navigable documentation website, built with MkDocs (Material theme) and
published on GitHub Pages.

**Live site:** https://gilntk.github.io/mpc-manual-to-web/

## Status

Work in progress. The structure extraction and site build are working; image
handling and a number of output decisions are still to be completed, so some
pages won't yet match the source closely.

## Why

A PDF records how a document looks, not what its parts are: headings, lists,
and body text are just positioned text. This manual was most likely written in
Microsoft Word by several authors over many releases, with templates that
evolved along the way, so the same kind of content doesn't always look the same
from section to section.

This project recovers the document's structure from its rendered appearance. I
studied how each kind of content actually appears in the PDF, then wrote
extraction rules that identify it and output consistent, repeatable HTML. The
result reads as one uniform document, with navigation and search, instead of a
long PDF that shows its seams.

## How it works

1. `scripts/dump_toc.py` prints the PDF's bookmark tree, to check the structure
   before extracting.
2. `scripts/extraction.py` walks the bookmark tree to find where each section
   starts and ends, then applies rules that infer each element's role from how
   it appears on the page. It outputs consistent HTML that approximates the
   source's styling, and drops page numbers and running header images.
3. MkDocs builds the site from those pages, with navigation in `mkdocs.yml`
   mirroring the manual's hierarchy: Introduction, Tutorial, Operation,
   Hardware Features, Appendix, and Addenda.
4. The built site is published to GitHub Pages.

## Usage

    pip install pymupdf pyyaml mkdocs-material
    # place the manual at input/manual.pdf
    python scripts/dump_toc.py
    python scripts/extraction.py
    mkdocs serve        # preview locally
    mkdocs gh-deploy    # publish to GitHub Pages

## Notes

The MPC user guide is published by Akai Professional, which owns its content
and trademarks. This project isn't affiliated with or endorsed by Akai
Professional. The code contains none of their material; it's built to work with
their publicly available user guide. The source PDF and the generated pages are
not stored in this repository's main branch.
