# MCP Platform API Documentation

This directory contains the generated API documentation for all MCP Platform services.

## Quick Access

- [**View All API Documentation**](./index.html) - Main documentation index
- [Text Summarization Service - ReDoc](./text-summarization-redoc.html)
- [Context Service - ReDoc](./context-service-redoc.html)

## OpenAPI Specifications

- [Text Summarization Service - OpenAPI JSON](./text-summarization-openapi.json)
- [Context Service - OpenAPI JSON](./context-service-openapi.json)

## Development URLs

When running services locally in development mode:

- **Text Summarization Service**:
  - Swagger UI: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc
  - OpenAPI JSON: http://localhost:8000/openapi.json

- **Context Service**:
  - Swagger UI: http://localhost:8001/docs
  - ReDoc: http://localhost:8001/redoc
  - OpenAPI JSON: http://localhost:8001/openapi.json

## Generating Documentation

To generate the API documentation:

```bash
# From the project root
make generate-docs
```

Or run the script directly:

```bash
python3 scripts/generate-api-docs.py
```

## What Gets Generated

The script generates:

1. **OpenAPI JSON files** - Machine-readable API specifications
2. **ReDoc HTML files** - Beautiful, interactive API documentation
3. **Index HTML file** - Landing page with links to all documentation

## Files in this Directory

- `index.html` - Main documentation landing page
- `text-summarization-openapi.json` - OpenAPI spec for Text Summarization Service
- `text-summarization-redoc.html` - ReDoc documentation for Text Summarization Service
- `context-service-openapi.json` - OpenAPI spec for Context Service
- `context-service-redoc.html` - ReDoc documentation for Context Service

## Requirements

The documentation generation requires:

- Python 3.9+
- FastAPI applications (services must be importable)
- All service dependencies installed

## Troubleshooting

If documentation generation fails:

1. Ensure all service dependencies are installed:
   ```bash
   cd services/text-summarization && make install
   cd services/context-service && make install
   ```

2. Check that the services can be imported without errors

3. Verify that the services are using FastAPI with proper OpenAPI integration

## ReDoc Features

The ReDoc documentation provides:

- Interactive API exploration
- Request/response examples
- Authentication information
- Error response documentation
- Model schemas and validation rules

## Integration with CI/CD

The documentation generation can be integrated into CI/CD pipelines to ensure documentation stays up-to-date with API changes.
