# scripts/dump_toc.py
import fitz  # pymupdf's import name

doc = fitz.open("input/manual.pdf")
toc = doc.get_toc()

for level, title, page in toc:
    indent = "  " * (level - 1)
    print(f"{indent}{title} (p.{page})")

print(f"\nTotal entries: {len(toc)}")
