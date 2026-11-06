# MPC Manual to Web

A Python pipeline that converts the Akai MPC user guide from a single PDF into a
navigable documentation website, built with MkDocs (Material theme) and
published on GitHub Pages.

**Live site:** https://gilntk.github.io/mpc-manual-to-web/

## Why

A long PDF manual is hard to search and hard to read on screen. This project
splits it into topic-sized pages that follow the manual's own structure, with
navigation and search, while keeping the look of the original.

## How it works

1. `scripts/dump_toc.py` prints the PDF's bookmark tree, to check the structure
   before extracting.
2. `scripts/extraction.py` walks the bookmark tree, finds where each section
   starts and ends on the page, and outputs each section as HTML that
   approximates the source document's styling. It drops page numbers and
   running header images.
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

The source PDF and the generated pages are not stored in this repository's
main branch; it holds the conversion tooling.
