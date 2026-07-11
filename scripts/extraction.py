import fitz
import re
import yaml
from pathlib import Path

INPUT_PDF = "input/manual.pdf"
OUTPUT_DIR = Path("docs")
HEADER_FOOTER_MARGIN = 60
MKDOCS_YML = "mkdocs.yml"

def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug

def escape_html_chars(text):
    return text.replace("<", "&lt;").replace(">", "&gt;")

def normalize(s):
    return " ".join(s.split()).strip().lower()

def extract_y_from_view(view_str):
    if not view_str:
        return 0.0
    m = re.match(r"FitH,([\d.]+)", view_str)
    if m:
        return float(m.group(1))
    return 0.0

def is_page_number(text, y_pos, page_height):
    stripped = text.strip()
    if not re.fullmatch(r"\d{1,4}", stripped):
        return False
    near_top = y_pos < HEADER_FOOTER_MARGIN
    near_bottom = y_pos > (page_height - HEADER_FOOTER_MARGIN)
    return near_top or near_bottom

def is_header_image(bbox):
    y_pos = bbox[1]
    return y_pos < HEADER_FOOTER_MARGIN

def build_tree(toc_full):
    root = {"children": [], "title": None, "level": 0, "start_page": 1, "start_y": 0.0}
    stack = [root]
    for level, title, page, dest in toc_full:
        y = extract_y_from_view(dest.get("view", ""))
        node = {"title": title, "level": level, "start_page": page, "start_y": y, "children": []}
        while stack[-1]["level"] >= level:
            stack.pop()
        stack[-1]["children"].append(node)
        node["parent"] = stack[-1]
        stack.append(node)
    return root

def compute_end_boundary(node, doc_page_count, next_sibling_start=None, next_sibling_title=None):
    children = node["children"]
    for i, child in enumerate(children):
        if i + 1 < len(children):
            sib = children[i + 1]
            child_next_start = (sib["start_page"], sib["start_y"])
            child_next_title = sib["title"]
        else:
            child_next_start = next_sibling_start
            child_next_title = next_sibling_title
        compute_end_boundary(child, doc_page_count, child_next_start, child_next_title)

    if node["title"] is not None:
        if next_sibling_start:
            node["end_page"], node["end_y"] = next_sibling_start
        else:
            node["end_page"] = doc_page_count
            node["end_y"] = None
        node["next_sibling_title"] = next_sibling_title

def extract_content(doc, start_page, start_y, end_page, end_y, image_dir, image_prefix, skip_title=None, next_sibling_title=None):
    content_parts = []
    deferred_images = []
    image_counter = 0
    title_normalized = normalize(skip_title) if skip_title else None
    next_title_normalized = normalize(next_sibling_title) if next_sibling_title else None
    title_skipped = False
    EPS = 0.5

    for page_num in range(start_page - 1, end_page):
        current_page_1indexed = page_num + 1
        page = doc[page_num]
        page_height = page.rect.height
        text_blocks = page.get_text("dict")["blocks"]
        image_info = page.get_image_info(xrefs=True)

        text_items = []
        for block in text_blocks:
            if "lines" not in block or not block["lines"]:
                continue
            y_pos = block["bbox"][1]

            if current_page_1indexed == start_page and y_pos < start_y - EPS:
                continue
            if current_page_1indexed == end_page and end_y is not None and y_pos >= end_y - EPS:
                continue

            paragraph_lines = []
            paragraph_lines_raw = []
            for line in block["lines"]:
                line_text = ""
                line_text_raw = ""
                for span in line["spans"]:
                    text = escape_html_chars(span["text"])
                    is_bold = bool(span["flags"] & 2**4)
                    stripped = text.strip()
                    line_text_raw += text
                    if is_bold and stripped:
                        leading = text[:len(text) - len(text.lstrip())]
                        trailing = text[len(text.rstrip()):]
                        text = f"{leading}**{stripped}**{trailing}"
                    line_text += text
                if line_text.strip():
                    paragraph_lines.append(line_text)
                    paragraph_lines_raw.append(line_text_raw)

            if paragraph_lines:
                paragraph = " ".join(paragraph_lines)
                paragraph_raw = " ".join(paragraph_lines_raw)

                if is_page_number(paragraph_raw, y_pos, page_height):
                    continue

                if title_normalized and not title_skipped and normalize(paragraph_raw) == title_normalized:
                    title_skipped = True
                    continue

                if next_title_normalized and normalize(paragraph_raw) == next_title_normalized:
                    continue

                text_items.append((y_pos, paragraph))

        for img in image_info:
            bbox = img["bbox"]
            y_pos = bbox[1]

            if current_page_1indexed == start_page and y_pos < start_y - EPS:
                continue
            if current_page_1indexed == end_page and end_y is not None and y_pos >= end_y - EPS:
                continue
            if is_header_image(bbox):
                continue

            deferred_images.append(img)

        text_items.sort(key=lambda x: x[0])
        for _, paragraph in text_items:
            content_parts.append(paragraph)

    for payload in deferred_images:
        image_counter += 1
        xref = payload["xref"]
        try:
            base_image = doc.extract_image(xref)
            ext = base_image["ext"]
            img_bytes = base_image["image"]
            image_dir.mkdir(parents=True, exist_ok=True)
            img_filename = f"{image_prefix}-img{image_counter}.{ext}"
            img_path = image_dir / img_filename
            img_path.write_bytes(img_bytes)
            content_parts.append(f"![]({img_filename})")
        except Exception as e:
            content_parts.append(f"<!-- image extraction failed: {e} -->")

    return "\n\n".join(content_parts)

def write_node(node, doc, out_dir, path_parts):
    is_leaf = len(node["children"]) == 0
    title = node["title"]
    slug = slugify(title)
    heading = "#" * node["level"]

    if is_leaf:
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / f"{slug}.md"
        content = extract_content(
            doc, node["start_page"], node["start_y"],
            node["end_page"], node["end_y"],
            out_dir, slug, skip_title=title,
            next_sibling_title=node.get("next_sibling_title")
        )
        front_matter = f"---\ntitle: {title}\n---\n\n"
        # file_path.write_text(f"{heading} {title}\n\n{content}\n")
        file_path.write_text(f"{front_matter}{content}\n")
        node["has_intro_content"] = True
    else:
        section_dir = out_dir / slug
        section_dir.mkdir(parents=True, exist_ok=True)
        first_child = node["children"][0]
        content = extract_content(
            doc, node["start_page"], node["start_y"],
            first_child["start_page"], first_child["start_y"],
            section_dir, "index", skip_title=title,
            next_sibling_title=first_child["title"]
        )
        node["has_intro_content"] = bool(content.strip())

        if node["has_intro_content"]:
            index_path = section_dir / "index.md"
            front_matter = f"---\ntitle: {title}\n---\n\n"
            # index_path.write_text(f"{heading} {title}\n\n{content}\n")
            index_path.write_text(f"{front_matter}{content}\n")

        for child in node["children"]:
            write_node(child, doc, section_dir, path_parts + [slug])

def build_nav_entry(node, path_so_far):
    slug = slugify(node["title"])
    is_leaf = len(node["children"]) == 0

    if is_leaf:
        rel_path = "/".join(path_so_far + [f"{slug}.md"])
        return {node["title"]: rel_path}
    else:
        children_nav = []
        if node.get("has_intro_content"):
            children_nav.append("/".join(path_so_far + [slug, "index.md"]))
        for child in node["children"]:
            children_nav.append(build_nav_entry(child, path_so_far + [slug]))
        return {node["title"]: children_nav}

def write_nav_file(root, output_path="nav_snippet.yml"):
    nav = [build_nav_entry(child, []) for child in root["children"]]
    with open(output_path, "w") as f:
        yaml.dump({"nav": nav}, f, sort_keys=False, allow_unicode=True)
    return nav

def write_nav_to_mkdocs(nav, mkdocs_path=MKDOCS_YML):
    nav_yaml_str = yaml.dump({"nav": nav}, sort_keys=False, allow_unicode=True)
    mkdocs_file = Path(mkdocs_path)
    content = mkdocs_file.read_text() if mkdocs_file.exists() else ""
    idx = content.find("\nnav:")
    if idx != -1:
        content = content[:idx]
    content = content.rstrip() + "\n\n" + nav_yaml_str.rstrip() + "\n"
    mkdocs_file.write_text(content)

def main():
    doc = fitz.open(INPUT_PDF)
    toc_full = doc.get_toc(simple=False)
    toc_full = [entry for entry in toc_full if entry[1] != "Table of Contents"]

    root = build_tree(toc_full)
    compute_end_boundary(root, doc.page_count)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for top_level_node in root["children"]:
        write_node(top_level_node, doc, OUTPUT_DIR, [])

    nav = write_nav_file(root)
    write_nav_to_mkdocs(nav)

    print("Extraction complete. mkdocs.yml nav: updated, nav_snippet.yml written for reference.")

if __name__ == "__main__":
    main()
