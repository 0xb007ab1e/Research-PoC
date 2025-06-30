# Publishing Workflow

## Docs CI
- Use `markdown-lint-cli` for linting Markdown files.
- Employ `linkinator` to check for broken links.
- Use `mermaid-cli` to generate SVGs from Mermaid diagrams.

## Preview
- Set up auto-deployment of MkDocs-Material site to GitHub Pages for each PR for review at `/docs-preview/<branch>`.

## Review Gates
- Require at least two approvals on GitHub: one from the Tech Lead and one from Security. This can be enforced via GitHub branch protection rules.

## Release
- On tagging a release with `docs-vX.Y`, automate pushing to the `gh-pages` branch using GitHub Actions, and ensure that a PDF is uploaded.

## Archival
- Store a monthly snapshot in Amazon S3 with a Glacier Deep Archive lifecycle rule for long-term storage.
