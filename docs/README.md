# Documentation

This directory contains all project documentation organized according to our established conventions.

## Quick Start

1. **Read the conventions first**: Start with [`00-docs-conventions.md`](./00-docs-conventions.md)
2. **Find what you need**: Use the directory structure below
3. **Follow the naming pattern**: `<NN>-<topic>.md` for all new documents

## Directory Structure

```
docs/
├── 00-docs-conventions.md     # Documentation standards (READ FIRST)
├── 01-requirements.md         # Project requirements
├── README.md                  # This file
├── ai/                       # AI service documentation
├── api/                      # API documentation and specs
├── architecture/             # C4 model architectural views
├── oss/                      # Open source documentation
├── poc/                      # Proof of concept guides
├── publishing/               # Publishing documentation
├── security/                 # Security documentation
├── team/                     # Team information
├── timeline/                 # Project timeline and milestones
└── workflows/                # Process and workflow docs
```

## Creating New Documentation

1. Choose the appropriate directory
2. Use the naming convention: `<NN>-<topic>.md`
3. Follow the style guide in the conventions document
4. Use diagrams-as-code (PlantUML/Mermaid) for all diagrams
5. Run linting before committing: `markdownlint docs/**/*.md`

## Need Help?

- Check the conventions document for detailed guidelines
- Use the provided templates for consistency
- All documentation changes require peer review

---
*For detailed guidelines, see [Documentation Conventions](./00-docs-conventions.md)*
