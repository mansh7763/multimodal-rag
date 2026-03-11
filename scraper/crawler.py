"""Fetch HuggingFace course content directly from GitHub repos."""

import json
import os
import time
from pathlib import Path

import requests
from tqdm import tqdm

DATA_DIR = Path("data/raw_html")

# GitHub repos and their content paths
# Format: {slug: (github_owner/repo, content_path, file_extensions)}
COURSES = {
    "agents-course": {
        "repo": "huggingface/agents-course",
        "content_path": "units/en",
        "extensions": [".mdx", ".md"],
    },
    "smol-course": {
        "repo": "huggingface/smol-course",
        "content_path": "units",
        "extensions": [".mdx", ".md"],
    },
    "deep-rl-course": {
        "repo": "huggingface/deep-rl-class",
        "content_path": "units/en",
        "extensions": [".mdx", ".md"],
    },
    "audio-course": {
        "repo": "huggingface/audio-transformers-course",
        "content_path": "chapters/en",
        "extensions": [".mdx", ".md"],
    },
    "diffusion-course": {
        "repo": "huggingface/diffusion-models-class",
        "content_path": "",
        "extensions": [".md", ".ipynb"],
    },
    "computer-vision-course": {
        "repo": "huggingface/computer-vision-course",
        "content_path": "chapters",
        "extensions": [".mdx", ".md"],
    },
    "mcp-course": {
        "repo": "huggingface/mcp-course",
        "content_path": "units/en",
        "extensions": [".mdx", ".md"],
    },
    "cookbook": {
        "repo": "huggingface/cookbook",
        "content_path": "notebooks/en",
        "extensions": [".md", ".ipynb"],
    },
}

# GitHub API base
GITHUB_API = "https://api.github.com"


def _github_headers() -> dict:
    """Build headers for GitHub API. Uses token if available."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def list_repo_files(
    repo: str,
    content_path: str,
    extensions: list[str],
) -> list[dict]:
    """Recursively list all matching files in a GitHub repo path.

    Uses the Git Trees API for efficiency (single request for entire tree).
    """
    # Get the default branch SHA
    url = f"{GITHUB_API}/repos/{repo}/git/trees/main?recursive=1"
    resp = requests.get(url, headers=_github_headers())

    if resp.status_code == 404:
        # Try 'master' branch
        url = f"{GITHUB_API}/repos/{repo}/git/trees/master?recursive=1"
        resp = requests.get(url, headers=_github_headers())

    if resp.status_code != 200:
        print(f"  Failed to list files for {repo}: {resp.status_code}")
        return []

    tree = resp.json().get("tree", [])
    files = []

    for item in tree:
        if item["type"] != "blob":
            continue
        path = item["path"]

        # Filter by content path prefix
        if content_path and not path.startswith(content_path):
            continue

        # Filter by extension
        if not any(path.endswith(ext) for ext in extensions):
            continue

        # Skip non-English translations (files in language subdirs like /fr/, /es/)
        # but keep the content_path itself
        relative = path[len(content_path):].strip("/") if content_path else path
        parts = relative.split("/")
        # Skip if first part looks like a 2-letter language code (but not a unit/chapter dir)
        if len(parts) > 1 and len(parts[0]) == 2 and parts[0].isalpha():
            if parts[0] not in ("en",):
                continue

        files.append({
            "path": path,
            "sha": item["sha"],
            "size": item.get("size", 0),
        })

    return files


def download_file_content(repo: str, file_path: str) -> str | None:
    """Download raw file content from GitHub."""
    url = f"https://raw.githubusercontent.com/{repo}/main/{file_path}"
    resp = requests.get(url)

    if resp.status_code == 404:
        url = f"https://raw.githubusercontent.com/{repo}/master/{file_path}"
        resp = requests.get(url)

    if resp.status_code == 200:
        return resp.text

    print(f"  Failed to download {file_path}: {resp.status_code}")
    return None


def _extract_chapter_section(file_path: str, content_path: str) -> tuple[str, str]:
    """Extract chapter and section from the file path."""
    relative = file_path[len(content_path):].strip("/") if content_path else file_path
    parts = relative.split("/")

    if len(parts) >= 2:
        chapter = parts[0]  # e.g., "unit1", "chapter1"
        section = Path(parts[-1]).stem  # e.g., "introduction"
    elif len(parts) == 1:
        chapter = "index"
        section = Path(parts[0]).stem
    else:
        chapter = "unknown"
        section = "unknown"

    return chapter, section


def _extract_images_from_markdown(content: str, repo: str, file_path: str) -> list[str]:
    """Extract image URLs from markdown content, resolve relative paths."""
    import re

    image_urls = []
    # Match ![alt](url) and <img src="url">
    patterns = [
        r'!\[[^\]]*\]\(([^)]+)\)',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]

    base_dir = str(Path(file_path).parent)

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            url = match.group(1).strip()

            if url.startswith("http"):
                image_urls.append(url)
            elif not url.startswith("data:"):
                # Resolve relative path
                resolved = f"https://raw.githubusercontent.com/{repo}/main/{base_dir}/{url}"
                image_urls.append(resolved)

    return image_urls


def scrape_course(course_slug: str) -> list[dict]:
    """Fetch all content files for a single course from GitHub."""
    if course_slug not in COURSES:
        print(f"Unknown course: {course_slug}")
        return []

    config = COURSES[course_slug]
    repo = config["repo"]
    content_path = config["content_path"]
    extensions = config["extensions"]

    print(f"\n--- Fetching: {course_slug} from {repo} ---")

    # List all matching files
    files = list_repo_files(repo, content_path, extensions)
    print(f"  Found {len(files)} content files")

    if not files:
        return []

    pages = []
    for file_info in tqdm(files, desc=f"  Downloading {course_slug}"):
        content = download_file_content(repo, file_info["path"])
        if not content:
            continue

        chapter, section = _extract_chapter_section(file_info["path"], content_path)
        image_urls = _extract_images_from_markdown(content, repo, file_info["path"])

        # Build HF Learn URL (best guess)
        hf_url = f"https://huggingface.co/learn/{course_slug}/{chapter}/{section}"

        pages.append({
            "url": hf_url,
            "github_url": f"https://github.com/{repo}/blob/main/{file_info['path']}",
            "course": course_slug,
            "chapter": chapter,
            "section": section,
            "title": f"{course_slug} > {chapter} > {section}",
            "path": file_info["path"],
            "content": content,
            "image_urls": image_urls,
            "format": Path(file_info["path"]).suffix,
        })

        # Small delay to avoid GitHub rate limiting
        time.sleep(0.1)

    return pages


def scrape_all_courses(course_slugs: list[str] | None = None) -> list[dict]:
    """Fetch all courses and save to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    targets = course_slugs or list(COURSES.keys())
    all_pages = []

    for slug in targets:
        pages = scrape_course(slug)
        all_pages.extend(pages)

        # Save per-course
        course_dir = DATA_DIR / slug
        course_dir.mkdir(parents=True, exist_ok=True)
        for i, page_data in enumerate(pages):
            filepath = course_dir / f"page_{i:04d}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)

        print(f"  Saved {len(pages)} pages for {slug}")

    print(f"\nTotal pages fetched: {len(all_pages)}")
    return all_pages


if __name__ == "__main__":
    scrape_all_courses()
