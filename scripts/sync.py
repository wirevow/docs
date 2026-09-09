#!/usr/bin/env python3
"""Rebuild the Mintlify tree from the product repos' docs/ folders.

Source of truth stays in wirevow/gitvow, wirevow/gitvow-provider-facts and wirevow/gitvow-skills
(which also feed GitHub Pages). This script converts MkDocs Markdown to Mintlify MDX:
frontmatter from the first H1, extensionless links, angle-bracket placeholders escaped outside code.
Usage: scripts/sync.py [--root ~/Documents/personal]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

SOURCES = {
    "gitvow": "gitvow/docs",
    "provider-facts": "gitvow-provider-facts/docs",
}
SKIP_DIRS = {"stylesheets", "assets"}


def split_code(text: str):
    """Yield (segment, is_code) so prose-only rewrites never touch fences or inline code."""
    parts = re.split(r"(```.*?```|~~~.*?~~~|`[^`\n]*`)", text, flags=re.S)
    for p in parts:
        yield p, p.startswith("`") or p.startswith("~~~")


def prose_fix(seg: str) -> str:
    # <placeholder> in prose would be parsed as JSX; wrap in inline code.
    seg = re.sub(r"<([a-z][a-z0-9-]*(?: [a-z][a-z0-9-]*)*)>", r"`<\1>`", seg)
    seg = re.sub(r"<([A-Z][A-Za-z]*)>", r"`<\1>`", seg)
    seg = seg.replace("<!--", "{/*").replace("-->", "*/}")
    # stray braces in prose (e.g. {i}) -> inline code
    seg = re.sub(r"(?<!`)\{([^}\n]{1,40})\}(?!`)", r"`{\1}`", seg)
    return seg


def fix_links(seg: str, tab: str, rel_dir: str) -> str:
    def repl(m):
        text, target = m.group(1), m.group(2)
        if re.match(r"^[a-z]+:", target) or target.startswith("#") or target.startswith("/"):
            return m.group(0)
        path, _, anchor = target.partition("#")
        if not path.endswith(".md"):
            return m.group(0)
        path = path[:-3]
        if path.endswith("/index"):
            path = path[: -len("/index")] or "."
        joined = os.path.normpath(os.path.join(rel_dir, path)) if rel_dir else os.path.normpath(path)
        if joined in (".", "index"):
            joined = ""
        new = "/" + tab + ("/" + joined if joined else "")
        new = new.replace("/ARCHITECTURE", "/architecture")
        return f"[{text}]({new}{'#' + anchor if anchor else ''})"

    return re.sub(r"\[([^\]]*)\]\(([^)\s]+)\)", repl, seg)


def convert(md: str, tab: str, rel_dir: str, fallback_title: str) -> str:
    title = fallback_title
    m = re.search(r"^# (.+)$", md, re.M)
    if m:
        title = m.group(1).strip().replace('"', "'")
        md = md[: m.start()] + md[m.end():]
    desc = ""
    body = md.strip("\n")
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    cands = re.findall(r"^(?![#|>\-!\s`]|\* )([^\n]{40,})$", prose, re.M)
    cands = [c for c in cands if not c.rstrip().endswith(":")] or cands
    if cands:
        raw = cands[0]
        d = re.sub(r"<[^>]*>", "", raw)
        d = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", d)
        d = re.sub(r"[`*_\[\]{}]", "", d).strip()
        if len(d) <= 200:
            # the whole lede becomes the subtitle Mintlify renders under the title: drop it from the body
            body = body.replace(raw + "\n", "", 1).replace(raw, "", 1)
        else:
            cut = d[:160]
            d = cut[: cut.rfind(". ") + 1] if ". " in cut else cut[: cut.rfind(" ")]
            # move the first sentence up into the subtitle and let the paragraph continue from the second
            m2 = re.match(r"^(.+?\.)\s+(?=[A-Z`*\[])", raw)
            if m2 and re.sub(r"[`*_\[\]{}<>]", "", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", m2.group(1))).strip().rstrip(".") == d.strip().rstrip("."):
                body = body.replace(raw, raw[m2.end():], 1)
        desc = d.strip().rstrip(".").replace('"', "'")
    out = []
    for seg, is_code in split_code(body):
        if not is_code:
            seg = fix_links(prose_fix(seg), tab, rel_dir)
        out.append(seg)
    fm = f'---\ntitle: "{title}"\n' + (f'description: "{desc}"\n' if desc else "") + "---\n\n"
    return fm + "".join(out).strip("\n") + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/Documents/personal"))
    args = ap.parse_args()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for tab, src in SOURCES.items():
        src_dir = os.path.join(args.root, src)
        dst_dir = os.path.join(here, tab)
        if not os.path.isdir(src_dir):
            print(f"missing {src_dir}", file=sys.stderr)
            return 1
        if os.path.isdir(dst_dir):
            shutil.rmtree(dst_dir)
        for dirpath, dirnames, filenames in os.walk(src_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            rel_dir = os.path.relpath(dirpath, src_dir)
            rel_dir = "" if rel_dir == "." else rel_dir
            for fn in sorted(filenames):
                if not fn.endswith(".md"):
                    continue
                with open(os.path.join(dirpath, fn)) as fh:
                    md = fh.read()
                stem = fn[:-3]
                stem = "architecture" if stem == "ARCHITECTURE" else stem
                os.makedirs(os.path.join(dst_dir, rel_dir), exist_ok=True)
                with open(os.path.join(dst_dir, rel_dir, stem + ".mdx"), "w") as fh:
                    fh.write(convert(md, tab, rel_dir, stem.replace("-", " ").title()))
    # skills: README + each SKILL.md
    sk = os.path.join(args.root, "gitvow-skills")
    dst = os.path.join(here, "skills")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    with open(os.path.join(sk, "README.md")) as fh:
        readme = fh.read()
    with open(os.path.join(dst, "index.mdx"), "w") as fh:
        fh.write(convert(readme, "skills", "", "gitvow skills"))
    for name in sorted(os.listdir(os.path.join(sk, "skills"))):
        p = os.path.join(sk, "skills", name, "SKILL.md")
        if not os.path.exists(p):
            continue
        with open(p) as fh:
            body = fh.read()
        # strip the skill's own frontmatter; keep description as page description
        fm = re.match(r"^---\n(.*?)\n---\n", body, re.S)
        desc = ""
        if fm:
            dm = re.search(r"^description:\s*(.+)$", fm.group(1), re.M)
            desc = dm.group(1).strip().strip("\"'") if dm else ""
            body = body[fm.end():]
        page = convert(body, "skills", "", name)
        if desc and "description:" not in page.split("---")[1]:
            page = page.replace("---\n\n", f'description: "{desc[:160]}"\n---\n\n', 1)
        with open(os.path.join(dst, name + ".mdx"), "w") as fh:
            fh.write(page)
    print("synced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
