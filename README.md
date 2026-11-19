# software-from-hell

The GitHub Pages site behind softwarefromhell.com: a Jekyll static site
(articles in `_articles/`, one shared in-house layout in `_layouts/site.html`).
Push to `main` and Pages publishes it (no local build step in production;
`jekyll build` is for local preview only).

## The publishing pipeline

- `main` **is** the live site. The editorial gate is git.
- Drafts live on the `drafts` branch: an article is one markdown file in
  `_articles/` (front matter: `title`, `description`, `section`, `image`, `alt`,
  `plate_sub`), and its hero image in `images/<slug>/` (PNG + its caption JSON
  sidecar). **Every path in an article is `../`-relative** (`../mem/`,
  `../images/<slug>/hero.png`) and every path in a root page is bare-relative
  (`hero.png`) — the law is that the same tree renders identically at a domain
  root and prefix-mounted (the tailnet `/sfh-staging/` preview). No relative_url,
  no depth computation in the layout. Rendered locally, then shown to the owner; nothing merges to `main`
  until the owner approves the words *and* picks the hero take.
- The landing cards generate from `_data/landing.yml` (the content plan, made
  machine-readable) cross-referenced against `_articles/`: a slot with a post is
  live + linked, a slot without one is coming-soon. Publish an article and the
  card updates itself — the catalog is never hand-edited.
- Hero images are rendered by the local `ideogram-4-mflux` engine per the recipe
  in the site spec (1280x640, sepia watercolor plate, subject off dead-center).
