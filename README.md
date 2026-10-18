# Sourabh Bose — academic homepage

Minimal static academic homepage on GitHub Pages. No build tools or external dependencies.

- `index.html`: short bio and My blog, with the DP visualization handbook first.
- `research.html`: complete resume publication list, research projects, education, academic appointments, service, and recognition.
- `teaching.html`: courses taught and corresponding WSU course lookup links.
- `style.css`: shared minimal styles.
- `resume.pdf`: unchanged resume supplied in Downloads.
- `publications/dynamic_programming_visualization_handbook.pdf`: unchanged handbook.

GitHub Pages serves the repository root on `main`; push changes to publish.
For local preview, run `python3 -m http.server 8000` here.

Content was checked against the supplied resume and official WSU faculty profile.
IEEE titles, authors, and publisher destinations were verified against publisher-deposited Crossref DOI metadata. IEEE Xplore blocks automated full-page retrieval. The FLAIRS paper links to the AAAI publisher PDF; the dissertation links to UTA MavMatrix; PerHealth service links to the workshop proceedings committee listing.
Course names and lookup destinations were checked against the WSU catalog. CS 697AB is the former Machine Learning number; CS 410 and CS 510 have distinct current catalog titles.

Replace PDFs in place to preserve their public links. Only public homepage content and the two explicitly requested PDFs are included.

The main page is the navigation hub. Every HTML subpage links back home; handbook entry points and the single resume link appear only on the main page; handbook pages have their own reading navigation.

## Handbook: PDF and HTML

The main page offers **Read online** and **Download PDF**. The online edition has
seven chapter pages, contents, section anchors, and Previous / Contents / Next /
Home navigation. Equations use native MathML; diagrams use local vector SVGs.
It needs no JavaScript, CDN, or website build service.

### Rebuild HTML from the source snapshot

Install Python dependencies from `tools/handbook-requirements.txt`, then run:

```sh
python tools/build_handbook.py
```

This uses `handbook/source/content.json` and the checked-in SVG assets. The
snapshot preserves the original LaTeX prose, code, captions, and diagram source.

### Refresh from the PDF's original sources

After rebuilding the chapter PDFs and master handbook in Organized_materials:

```sh
/path/to/Organized_materials/.venv/bin/python tools/build_handbook.py --materials-root /path/to/Organized_materials
```

This imports the same chapter generators used by the PDF, verifies their LaTeX
matches the saved sources, and regenerates the snapshot and standalone diagram
SVGs. LuaLaTeX must be on PATH. Intermediate diagram PDFs are stored only in the
materials workspace's `tmp/handbook-html`; they are not published. Existing source
PDFs and the downloadable handbook are not modified by the HTML build.

When updating both editions, also replace the public PDF at its existing path:
`publications/dynamic_programming_visualization_handbook.pdf`. Commit generated
HTML, SVGs, the source snapshot, and the updated PDF together, then push `main`.
