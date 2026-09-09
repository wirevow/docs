# wirevow-docs

Mintlify site for the Wirevow documentation (gitvow, gitvow-provider-facts, gitvow-skills). **Pilot.**

The Markdown source of truth lives in the product repositories and continues to publish to GitHub Pages
(https://wirevow.dev/gitvow/, https://wirevow.dev/gitvow-provider-facts/). This repository is generated from them:

```sh
scripts/sync.py            # rebuild gitvow/, provider-facts/, skills/ from ../gitvow, ../gitvow-provider-facts, ../gitvow-skills
npx mint dev               # preview at http://localhost:3000
npx mint broken-links      # check internal links
```

Do not edit the generated `.mdx` pages here; fix the Markdown in the product repository and re-run the sync.
Hand-written files: `docs.json`, `wirevow.css`, `images/`, `favicon.svg`, `scripts/sync.py`.
