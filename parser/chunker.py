"""Parse markdown/MDX course files into structured chunks."""

import json
import re
from pathlib import Path

from config import settings


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _strip_mdx_components(text: str) -> str:
    """Remove MDX/JSX components like <Tip>, <FrameworkContent>, etc."""
    # Remove self-closing tags: <Component />
    text = re.sub(r"<\w+[^>]*/\s*>", "", text)
    # Remove opening/closing tags but keep inner content
    text = re.sub(r"</?(?:Tip|Warning|FrameworkContent|Docstring|Youtube|CourseFloatingBanner|Iframe)[^>]*>", "", text, flags=re.IGNORECASE)
    return text


def split_markdown_by_headings(content: str) -> list[dict]:
    """Split markdown into sections by ## and ### headings.

    Returns list of:
    {
        "heading": "Section Title",
        "heading_level": 2 or 3,
        "body": "section content...",
    }
    """
    # Clean MDX components
    content = _strip_mdx_components(content)

    # Split by headings (## or ###)
    pattern = r"^(#{2,3})\s+(.+)$"
    sections = []
    current = {"heading": "", "heading_level": 1, "body_lines": []}

    for line in content.split("\n"):
        match = re.match(pattern, line)
        if match:
            # Save previous section
            if current["body_lines"] or current["heading"]:
                current["body"] = "\n".join(current["body_lines"]).strip()
                del current["body_lines"]
                if current["body"]:
                    sections.append(current)

            level = len(match.group(1))
            heading = match.group(2).strip()
            current = {"heading": heading, "heading_level": level, "body_lines": []}
        else:
            current["body_lines"].append(line)

    # Last section
    if current["body_lines"]:
        current["body"] = "\n".join(current["body_lines"]).strip()
        del current["body_lines"]
        if current["body"]:
            sections.append(current)

    return sections


def _extract_elements(body: str) -> list[dict]:
    """Parse a section body into typed elements (text, code, image, table)."""
    elements = []
    lines = body.split("\n")
    i = 0
    text_buffer = []

    while i < len(lines):
        line = lines[i]

        # Code block
        if line.strip().startswith("```"):
            # Flush text buffer
            if text_buffer:
                text = "\n".join(text_buffer).strip()
                if text:
                    elements.append({"type": "text", "content": text})
                text_buffer = []

            code_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                code_lines.append(lines[i])  # closing ```
            elements.append({"type": "code", "content": "\n".join(code_lines)})
            i += 1
            continue

        # Image: ![alt](src)
        img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if img_match:
            if text_buffer:
                text = "\n".join(text_buffer).strip()
                if text:
                    elements.append({"type": "text", "content": text})
                text_buffer = []

            elements.append({
                "type": "image",
                "alt": img_match.group(1),
                "src": img_match.group(2),
            })
            i += 1
            continue

        # Table (starts with |)
        if line.strip().startswith("|"):
            if text_buffer:
                text = "\n".join(text_buffer).strip()
                if text:
                    elements.append({"type": "text", "content": text})
                text_buffer = []

            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            elements.append({"type": "table", "content": "\n".join(table_lines)})
            continue

        # Regular text
        text_buffer.append(line)
        i += 1

    # Flush remaining text
    if text_buffer:
        text = "\n".join(text_buffer).strip()
        if text:
            elements.append({"type": "text", "content": text})

    return elements


def sections_to_chunks(
    sections: list[dict],
    course: str,
    chapter: str,
    url: str,
    image_urls: list[str] | None = None,
) -> list[dict]:
    """Convert sections into chunks with hierarchical prefix.

    Rules:
    - Each section becomes a chunk
    - If section > max_chunk_tokens, split at element boundaries
    - If section < min_chunk_tokens, merge with next section
    - Code blocks stay with their preceding text
    """
    chunks = []
    buffer_elements = []
    buffer_heading = ""

    def _make_chunk(heading: str, elements: list[dict]) -> dict | None:
        text_parts = []
        has_code = False
        has_image = False
        chunk_image_srcs = []

        for el in elements:
            if el["type"] == "text":
                text_parts.append(el["content"])
            elif el["type"] == "code":
                text_parts.append(el["content"])
                has_code = True
            elif el["type"] == "table":
                text_parts.append(el["content"])
            elif el["type"] == "image":
                has_image = True
                chunk_image_srcs.append(el["src"])
                if el.get("alt"):
                    text_parts.append(f"[Image: {el['alt']}]")

        content = "\n\n".join(text_parts).strip()
        if not content:
            return None

        # Add hierarchical prefix
        prefix = f"{course} > {chapter} > {heading}" if heading else f"{course} > {chapter}"
        full_content = f"{prefix}\n\n{content}"

        return {
            "content": full_content,
            "metadata": {
                "course": course,
                "chapter": chapter,
                "section": heading,
                "url": url,
                "content_type": "code" if has_code else "text",
                "has_code": has_code,
                "has_image": has_image,
                "image_srcs": chunk_image_srcs,
            },
        }

    for section in sections:
        heading = section["heading"]
        elements = _extract_elements(section["body"])

        if not elements:
            continue

        # Estimate token count
        section_text = " ".join(
            el.get("content", el.get("alt", "")) for el in elements
        )
        token_count = _estimate_tokens(section_text)

        if token_count < settings.min_chunk_tokens:
            # Merge with buffer
            buffer_heading = buffer_heading or heading
            buffer_elements.extend(elements)
            continue

        # Flush buffer first by merging with current
        if buffer_elements:
            buffer_elements.extend(elements)
            chunk = _make_chunk(buffer_heading, buffer_elements)
            if chunk:
                chunks.append(chunk)
            buffer_elements = []
            buffer_heading = ""
            continue

        if token_count > settings.max_chunk_tokens:
            # Split at element boundaries
            current_elements = []
            current_tokens = 0

            for el in elements:
                el_text = el.get("content", el.get("alt", ""))
                el_tokens = _estimate_tokens(el_text)

                if current_tokens + el_tokens > settings.max_chunk_tokens and current_elements:
                    chunk = _make_chunk(heading, current_elements)
                    if chunk:
                        chunks.append(chunk)
                    current_elements = []
                    current_tokens = 0

                current_elements.append(el)
                current_tokens += el_tokens

            if current_elements:
                chunk = _make_chunk(heading, current_elements)
                if chunk:
                    chunks.append(chunk)
        else:
            chunk = _make_chunk(heading, elements)
            if chunk:
                chunks.append(chunk)

    # Flush remaining buffer
    if buffer_elements:
        chunk = _make_chunk(buffer_heading, buffer_elements)
        if chunk:
            chunks.append(chunk)

    return chunks


def process_scraped_page(page_data: dict) -> list[dict]:
    """Process a single scraped page JSON into chunks."""
    content = page_data.get("content", "")
    if not content:
        return []

    course = page_data["course"]
    chapter = page_data.get("chapter", "index")
    url = page_data["url"]
    image_urls = page_data.get("image_urls", [])

    sections = split_markdown_by_headings(content)

    # If no headings found, treat the whole content as one section
    if not sections:
        sections = [{"heading": page_data.get("section", ""), "heading_level": 2, "body": content}]

    chunks = sections_to_chunks(sections, course, chapter, url, image_urls)
    return chunks


def process_all_pages(data_dir: str = "data/raw_html") -> list[dict]:
    """Process all scraped pages into chunks."""
    data_path = Path(data_dir)
    all_chunks = []

    for course_dir in sorted(data_path.iterdir()):
        if not course_dir.is_dir():
            continue
        print(f"Processing {course_dir.name}...")
        page_count = 0
        for json_file in sorted(course_dir.glob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                page_data = json.load(f)
            chunks = process_scraped_page(page_data)
            all_chunks.extend(chunks)
            page_count += 1
        print(f"  {page_count} pages -> {len(all_chunks)} total chunks so far")

    print(f"\nTotal chunks created: {len(all_chunks)}")

    # Save chunks
    output_dir = Path("data/chunks")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "all_chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"Saved to data/chunks/all_chunks.json")
    return all_chunks


if __name__ == "__main__":
    process_all_pages()
