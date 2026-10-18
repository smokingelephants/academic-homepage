#!/usr/bin/env python3
"""Build the HTML handbook from the same chapter generators as the PDF.

Refresh content and SVGs with --materials-root /path/to/Organized_materials.
Without that flag, rebuild from the checked-in source/content.json snapshot.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import html
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from latex2mathml.converter import convert as mathml

SITE = Path(__file__).resolve().parents[1]
BOOK = SITE / "handbook"
SOURCE = BOOK / "source" / "content.json"
SLUGS = ["fibonacci", "knapsack", "edit-distance", "water-jugs", "matrix-chain", "tower-of-hanoi", "two-sets-ii"]
MODULES = ["fibonacci_notes", "knapsack_trace", "edit_distance_trace", "jug_problem_notes", "matrix_chain_trace", "hanoi_variation_notes", "two_sets_ii_notes"]


def group(s: str, i: int) -> tuple[str, int]:
    while i < len(s) and s[i].isspace():
        i += 1
    if i == len(s) or s[i] != "{":
        raise ValueError(f"Expected group at {s[i:i+70]!r}")
    start, depth = i + 1, 1
    i += 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if not depth:
                return s[start:i], i + 1
        i += 1
    raise ValueError("Unclosed LaTeX group")


def code_html(s: str) -> str:
    rows = []
    pattern = re.compile(r"\\hspace\*\{([\d.]+)em\}\\mbox")
    matches = list(pattern.finditer(s))
    unit = min((float(m[1]) for m in matches if float(m[1]) > 0), default=1.88) / 4
    for m in matches:
        text, _ = group(s, m.end())
        text = text.replace(r"\textbackslash{}", "\\").replace(r"\strut", "")
        text = re.sub(r"\\([ {}_%#&])", r"\1", text)
        rows.append(" " * round(float(m[1]) / unit) + text)
    return '<pre><code class="language-python">' + html.escape("\n".join(rows)) + "</code></pre>"


def table_html(spec: str) -> str:
    # All source tables use a single header row, followed by \hline.
    spec = spec.replace(r"\hline", "")
    rows = re.split(r"\\\\", spec)
    out = []
    for row in rows:
        if not row.strip():
            continue
        cells = re.split(r"(?<!\\)&", row)
        tag = "th" if not out else "td"
        out.append("<tr>" + "".join(f"<{tag}>" + inline(c) + f"</{tag}>" for c in cells) + "</tr>")
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="Comparison table"><table>' + "".join(out) + "</table></div>"


def inline(s: str) -> str:
    out, i = [], 0
    declarations = {"sffamily", "selectfont", "raggedright", "raggedleft", "centering", "bfseries", "strut", "noindent", "vfill", "hfill", "hrule"}
    while i < len(s):
        c = s[i]
        if s.startswith("``", i) or s.startswith("''", i):
            out.append("“" if s[i] == "`" else "”")
            i += 2
        elif c == "{":
            content, i = group(s, i)
            out.append(code_html(content) if r"\ttfamily" in content else inline(content))
        elif c == "}":
            raise ValueError("Unexpected closing brace")
        elif c == "$":
            j = i + 1
            while j < len(s) and (s[j] != "$" or s[j-1] == "\\"):
                j += 1
            if j == len(s):
                raise ValueError("Unclosed math")
            formula = s[i+1:j]
            out.append(mathml(formula))
            i = j + 1
        elif c == "%":
            j = s.find("\n", i)
            i = len(s) if j == -1 else j + 1
        elif c == "\\":
            m = re.match(r"\\([a-zA-Z]+|.)", s[i:], re.S)
            if not m:
                raise ValueError("Trailing backslash")
            cmd = m[1]
            i += len(m[0])
            if cmd in declarations:
                continue
            if cmd == "par":
                out.append("\n\n")
            elif cmd in {" ", ";", ",", "quad", "qquad"}:
                out.append(" ")
            elif cmd in {"_", "%", "#", "&", "{", "}"}:
                out.append(html.escape(cmd))
            elif cmd == "\\":
                out.append("<br>")
            elif cmd in {"vspace", "hspace"}:
                if i < len(s) and s[i] == "*":
                    i += 1
                _, i = group(s, i)
                out.append(" ")
            elif cmd in {"fontsize", "renewcommand", "addcontentsline"}:
                for _ in range(3 if cmd == "addcontentsline" else 2):
                    _, i = group(s, i)
            elif cmd in {"color", "hypersetup", "pagenumbering", "thispagestyle"}:
                _, i = group(s, i)
            elif cmd == "textcolor":
                _, i = group(s, i)
                body, i = group(s, i)
                out.append(inline(body))
            elif cmd in {"textbf", "texttt", "emph", "section"}:
                if i < len(s) and s[i] == "*":
                    i += 1
                body, i = group(s, i)
                tag = {"textbf": "strong", "texttt": "code", "emph": "em", "section": "h2"}[cmd]
                out.append(f"<{tag}>" + inline(body) + f"</{tag}>")
            elif cmd == "begin":
                env, i = group(s, i)
                if env == "tabular":
                    _, i = group(s, i)
                    j = s.index(r"\end{tabular}", i)
                    out.append(table_html(s[i:j]))
                    i = j + len(r"\end{tabular}")
                elif env == "itemize":
                    out.append("<ul>")
                elif env != "center":
                    raise ValueError(f"Unsupported environment: {env}")
            elif cmd == "end":
                env, i = group(s, i)
                if env == "itemize":
                    out.append("</li></ul>")
                elif env != "center":
                    raise ValueError(f"Unsupported end environment: {env}")
            elif cmd == "item":
                out.append("</li><li>" if "<li>" in "".join(out) else "<li>")
            elif cmd == "tikz":
                if s[i] == "[":
                    i = s.index("]", i) + 1
                _, i = group(s, i)
            elif cmd in {"clearpage", "tableofcontents"}:
                pass
            else:
                raise ValueError(f"Unsupported text command: {cmd}: {s[max(0,i-20):i+60]!r}")
        else:
            out.append(html.escape(c))
            i += 1
    return "".join(out)


def prose(s: str) -> str:
    s = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", "", s, flags=re.S)
    result = inline(s)
    blocks = []
    def protect(match):
        blocks.append(match[0])
        return "\n\n" + f"BOOKBLOCK{len(blocks)-1}TOKEN" + "\n\n"
    result = re.sub(r'<pre>.*?</pre>|<div class="table-scroll".*?</div>|<h2>.*?</h2>', protect, result, flags=re.S)
    result = re.sub(r'(</?(?:ul|li)>)', r'\n\n\1\n\n', result)
    final = []
    for part in re.split(r"\n\s*\n", result):
        part = re.sub(r"\s+", " ", part).strip()
        if not part:
            continue
        token = re.fullmatch(r"BOOKBLOCK(\d+)TOKEN", part)
        if token:
            final.append(blocks[int(token[1])])
        elif part in {"<ul>", "</ul>", "<li>", "</li>"}:
            final.append(part)
        else:
            final.append("<p>" + part + "</p>")
    return "\n".join(final)



def refresh(materials: Path) -> dict:
    import pymupdf
    sys.path.insert(0, str(materials / "tools"))
    master = importlib.import_module("generate_dp_handbook")
    data = {"introduction": master.INTRODUCTION.split(r"\tableofcontents")[0], "chapters": []}
    assets = BOOK / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for chapter, module_name, slug in zip(master.CHAPTERS, MODULES, SLUGS):
        module = importlib.import_module("generate_" + module_name)
        original = module.latex_frame_box
        blocks = []
        def capture(title, body, footer="", **kwargs):
            tex = original(title, body, footer, **kwargs)
            blocks.append({"title": title, "body": body, "footer": footer, "tex": tex})
            return tex
        module.latex_frame_box = capture
        try:
            document = module.document()
        finally:
            module.latex_frame_box = original
        # Some generators construct later rows first; document order is authoritative.
        blocks.sort(key=lambda b: document.index(b["tex"]))
        source_tex = materials / "output" / "latex" / chapter.pdf.replace(".pdf", ".tex")
        if document != source_tex.read_text():
            raise ValueError(f"{source_tex.name} is out of sync; rebuild the PDF chapters first")
        pdf = pymupdf.open(materials / "output" / "pdf" / chapter.pdf)
        rectangles = []
        for number, page in enumerate(pdf):
            matches = [d["rect"] for d in page.get_drawings()
                       if d["fill"] == (1, 1, 1) and len(d["items"]) == 1
                       and d["items"][0][0] == "re" and d["rect"].width > 180 and d["rect"].height > 80]
            rectangles.extend((number, r) for r in sorted(matches, key=lambda r: (round(r.y0 / 4), r.x0)))
        assert len(blocks) == len(rectangles), (slug, len(blocks), len(rectangles))
        diagrams = []
        for number, (block, (page_number, rect)) in enumerate(zip(blocks, rectangles), 1):
            block.pop("tex")
            block["page"] = page_number + 1
            if r"\begin{tikzpicture}" in block["body"]:
                name = f"{slug}-{number:02}.svg"
                block["image"] = name
                pictures = re.findall(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", block["body"], flags=re.S)
                assert len(pictures) == 1, (slug, number)
                diagrams.append((block, pictures[0]))
        if slug == "matrix-chain":
            name = "matrix-chain-complete-tree.svg"
            special = {"title": "Complete naive recursion tree", "body": module.render_full_tree(), "footer": r"81 call occurrences and 40 partition nodes. Blue: $k=1$ (66); purple: $k=2$ (109); gold: $k=3$ (44, optimal); teal: $k=4$ (62). Bold gold: $(A(BC))(DE)$. Bold teal: $((A(BC))D)E$. Repeated $(i,j)$ circles are distinct calls; a partition requires both child branches.", "image": name, "page": 7}
            blocks.insert(17, special)
            diagrams.append((special, module.render_full_tree()))
        # Export TikZ directly on large pages, then crop to actual painted bounds.
        # This avoids inheriting a printed frame's clipping or repeated prose.
        if diagrams:
            executable = shutil.which("lualatex")
            if not executable:
                raise RuntimeError("lualatex is required to refresh diagram SVGs")
            work = materials / "tmp" / "handbook-html"
            work.mkdir(parents=True, exist_ok=True)
            preamble = module.PREAMBLE.split(r"\begin{document}")[0]
            tex = preamble + r"\geometry{paperwidth=600mm,paperheight=600mm,margin=40mm}" + "\n" + r"\begin{document}\pagestyle{empty}" + "\n"
            tex += "\n\\clearpage\n".join(r"\noindent " + picture for _, picture in diagrams)
            tex += "\n" + r"\end{document}"
            (work / (slug + ".tex")).write_text(tex)
            env = {**os.environ, "TEXMFVAR": str(materials / ".texlive" / "texmf-var"), "TEXMFCONFIG": str(materials / ".texlive" / "texmf-config")}
            result = subprocess.run([executable, "-interaction=nonstopmode", "-halt-on-error", slug + ".tex"], cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
            if result.returncode:
                raise RuntimeError(result.stdout[-3000:])
            rendered = pymupdf.open(work / (slug + ".pdf"))
            assert len(rendered) == len(diagrams), (slug, len(rendered), len(diagrams))
            for number, (block, _) in enumerate(diagrams):
                diagram_page = rendered[number]
                bounds = pymupdf.Rect()
                for kind, box in diagram_page.get_bboxlog():
                    if kind != "ignore-text":
                        bounds |= pymupdf.Rect(box)
                bounds = (bounds + (-4, -4, 4, 4)) & diagram_page.rect
                crop = pymupdf.open()
                target = crop.new_page(width=bounds.width, height=bounds.height)
                target.show_pdf_page(target.rect, rendered, number, clip=bounds)
                (assets / block["image"]).write_text(target.get_svg_image(text_as_path=True))
                block["width"], block["height"] = round(bounds.width), round(bounds.height)
                crop.close()
            rendered.close()
            print(f"Exported {len(diagrams)} diagrams for {slug}.", flush=True)
        banner = document.split(r"\begin{document}", 1)[1].split(r"\begin{minipage}", 1)[0]
        legends = []
        for match in re.finditer(r"\\textcolor", banner):
            _, end = group(banner, match.end())
            legend, _ = group(banner, end)
            legends.append(legend)
        data["chapters"].append({**asdict(chapter), "slug": slug, "legend": "; ".join(legends), "preamble": module.PREAMBLE, "blocks": blocks})
        pdf.close()
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data


def navigation(chapters: list, index: int | None) -> str:
    links = []
    if index is not None:
        links.append('<a rel="prev" href="' + (chapters[index-1]["slug"] + ".html" if index else "index.html") + '">← Previous</a>')
    links.extend(['<a href="index.html">Contents</a>', '<a href="../index.html">Home</a>'])
    if index is None or index + 1 < len(chapters):
        next_slug = chapters[0 if index is None else index + 1]["slug"]
        links.append(f'<a rel="next" href="{next_slug}.html">Next →</a>')
    return '<nav class="book-nav" aria-label="Handbook navigation">' + " · ".join(links) + "</nav>"


def page(title: str, content: str, nav: str) -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{html.escape(title)} — Dynamic Programming Visualization Handbook by Sourabh Bose.">
<title>{html.escape(title)} — DP Visualization Handbook</title>
<link rel="stylesheet" href="../style.css">
<link rel="stylesheet" href="book.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header><p class="book-title">Dynamic Programming Visualization Handbook</p>{nav}</header>
<main id="main">{content}</main>
<footer>{nav}<p>© 2026 Dr. Sourabh Bose</p></footer>
</body>
</html>
'''


def build(data: dict) -> None:
    chapters = data["chapters"]
    toc = "<ol>" + "".join(f'<li><a href="{c["slug"]}.html">{html.escape(c["title"])}</a><p class="description">{html.escape(c["subtitle"])}</p></li>' for c in chapters) + "</ol>"
    intro = prose(data["introduction"])
    content = '<h1>Dynamic Programming Visualization Handbook</h1><p>Sourabh Bose · 2026</p><h2>Contents</h2>' + toc + intro
    content += '<p>Diagrams retain the original vector artwork. Select a diagram to open it at full size; text, code, and tables are available directly on these pages.</p>'
    (BOOK / "index.html").write_text(page("Contents", content, navigation(chapters, None)))
    for index, chapter in enumerate(chapters):
        headings, sections = [], []
        for number, block in enumerate(chapter["blocks"], 1):
            anchor = f"section-{number:02}"
            title = inline(block["title"])
            headings.append(f'<li><a href="#{anchor}">{title}</a></li>')
            body = prose(block["body"])
            if "image" in block:
                url = "assets/" + block["image"]
                alt = html.escape(chapter["title"] + ": " + block["title"], quote=True)
                body += f'<figure><a href="{url}" aria-label="Open diagram: {alt}"><img src="{url}" alt="{alt}" width="{block["width"]}" height="{block["height"]}" loading="lazy"></a><figcaption>Original diagram, source page {block["page"]}. <a href="{url}">Open full-size diagram</a>.</figcaption></figure>'
            if block["footer"]:
                body += '<div class="caption">' + prose(block["footer"]) + '</div>'
            sections.append(f'<section id="{anchor}"><h2>{title}</h2>{body}</section>')
        details = "".join('<dt>' + label + '</dt><dd>' + inline(chapter[key]) + '</dd>' for label, key in [('State', 'state'), ('Goal', 'goal'), ('Base cases', 'base')])
        contents = '<details class="chapter-toc"><summary>On this page</summary><ol>' + "".join(headings) + '</ol></details>'
        legend = '<p><strong>Diagram legend:</strong> ' + inline(chapter["legend"]) + '.</p>' if chapter.get("legend") else ''
        content = f'<h1>{chapter["number"]}. {html.escape(chapter["title"])}</h1><p><em>{html.escape(chapter["subtitle"])}</em></p><p>{html.escape(chapter["summary"])}</p><dl>{details}</dl>' + legend + contents + "\n".join(sections)
        (BOOK / (chapter["slug"] + ".html")).write_text(page(chapter["title"], content, navigation(chapters, index)))
    print(f"Built {len(chapters)} chapters, {sum(len(c['blocks']) for c in chapters)} sections, and contents.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials-root", type=Path)
    args = parser.parse_args()
    data = refresh(args.materials_root.resolve()) if args.materials_root else json.loads(SOURCE.read_text())
    build(data)
