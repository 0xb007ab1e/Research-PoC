# Documentation Conventions

This document establishes the conventions and standards for all documentation in this project.

## Directory Structure

The documentation is organized into the following directories under `/docs`:

- `/docs/architecture/` - High-level architectural views following C4 model
  - C4 Context diagrams
  - Container diagrams  
  - Component diagrams
  - Code diagrams
- `/docs/api/` - API documentation
  - OpenAPI YAML specifications
  - Markdown walkthroughs and examples
- `/docs/security/` - Security documentation
- `/docs/workflows/` - Process and workflow documentation
- `/docs/timeline/` - Project timeline and milestones
- `/docs/team/` - Team information and contacts

## File Naming Convention

All documentation files follow the naming pattern:

```
<NN>-<topic>.md
```

Where:
- `<NN>` = Two-digit ordering prefix (00, 01, 02, etc.)
- `<topic>` = Descriptive topic name using kebab-case

**Examples:**
- `00-docs-conventions.md`
- `01-project-overview.md`
- `02-getting-started.md`
- `10-context-diagram.md`
- `20-container-diagram.md`

## Markdown Style Guide

### Format Standards
- **Markdown Flavor**: GitHub Flavored Markdown (GFM)
- **Line Length**: 80-character soft wrap for improved readability
- **Encoding**: UTF-8

### Headings
- Use ATX-style headers (`#`, `##`, `###`)
- Include a single space after the hash symbols
- Use sentence case for headings

### Lists
- Use `-` for unordered lists
- Use `1.` for ordered lists
- Indent nested lists with 2 spaces

### Code Blocks
- Use fenced code blocks with language specification
- Example: ```yaml, ```json, ```bash

### Links
- Use descriptive link text (avoid "click here")
- Prefer relative links for internal documentation
- Use reference-style links for repeated URLs

## Diagrams as Code

All diagrams must be created using diagrams-as-code approaches for:
- Version control compatibility
- Easy maintenance and updates
- Consistent styling

### Supported Tools

#### PlantUML
- Preferred for architectural diagrams (C4 model)
- Use `.puml` extension for source files
- Include rendered PNG/SVG in documentation

#### Mermaid
- Preferred for flowcharts and simple diagrams
- Embed directly in Markdown using fenced code blocks
- Example:
  ```mermaid
  graph TD
    A[Start] --> B[Process]
    B --> C[End]
  ```

### Diagram Guidelines
- Include source files in same directory as documentation
- Use consistent naming: `<NN>-<topic>-diagram.puml` or similar
- Add alt text for accessibility
- Keep diagrams simple and focused

## Quality Assurance

### Automated Checks
- **Linting**: Use `markdown-lint-cli` for style consistency
- **Link Checking**: Automated link validation in CI pipeline
- **Spell Check**: Recommended but not enforced

### CI Integration
The following checks run automatically on documentation changes:
- Markdown linting (markdownlint)
- Link validation (markdown-link-check)
- Diagram compilation (PlantUML/Mermaid)

### Manual Review Process
- All documentation changes require peer review
- Focus on clarity, accuracy, and completeness
- Verify all links and references work correctly

## Content Guidelines

### Writing Style
- Use clear, concise language
- Write for your audience (technical vs. non-technical)
- Use active voice when possible
- Define acronyms on first use

### Structure
- Start with a brief overview/summary
- Use consistent section organization
- Include table of contents for longer documents
- End with relevant links or next steps

### Maintenance
- Review and update documentation regularly
- Mark outdated information clearly
- Archive obsolete documents rather than deleting

## Templates

### Standard Document Template
```markdown
# Document Title

Brief description of the document purpose.

## Overview
[Brief summary]

## [Main Content Sections]

## References
- [Related documents]
- [External links]

---
*Last updated: [Date]*
*Review date: [Date]*
```

### Architecture Document Template
```markdown
# [NN]-[component-name]

## Context
[Why this exists]

## Decisions
[Key architectural decisions]

## Diagrams
[Include relevant diagrams]

## Implementation
[Technical details]

## Alternatives Considered
[Other options evaluated]
```

## Tools and Setup

### Required Tools
- Text editor with Markdown support
- PlantUML (for diagram generation)
- Node.js and markdownlint-cli
- Git for version control

### Recommended Setup
```bash
# Install markdownlint
npm install -g markdownlint-cli

# Install PlantUML (requires Java)
# Download from: https://plantuml.com/download

# Lint documentation
markdownlint docs/**/*.md

# Generate PlantUML diagrams
plantuml docs/**/*.puml
```

---
*This document is living and should be updated as conventions evolve.*
