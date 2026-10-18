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

The main page is the navigation hub. Every HTML subpage links back home; the handbook and the single resume link appear only on the main page.
