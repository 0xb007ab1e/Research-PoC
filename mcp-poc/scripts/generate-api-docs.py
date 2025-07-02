#!/usr/bin/env python3
"""
Generate OpenAPI JSON documentation for MCP services.

This script generates OpenAPI JSON documentation that can be used with
ReDoc or other API documentation tools.
"""

import json
import sys
import os
from pathlib import Path

# Add the services to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "text-summarization"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "context-service"))

def generate_text_summarization_openapi():
    """Generate OpenAPI JSON for text summarization service."""
    try:
        from main import app
        return app.openapi()
    except ImportError as e:
        print(f"Error importing text-summarization service: {e}")
        return None

def generate_context_service_openapi():
    """Generate OpenAPI JSON for context service."""
    try:
        from main import app
        return app.openapi()
    except ImportError as e:
        print(f"Error importing context service: {e}")
        return None

def save_openapi_json(service_name, openapi_spec, output_dir):
    """Save OpenAPI specification to JSON file."""
    if not openapi_spec:
        print(f"No OpenAPI spec available for {service_name}")
        return False
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{service_name}-openapi.json"
    
    try:
        with open(output_file, 'w') as f:
            json.dump(openapi_spec, f, indent=2)
        print(f"Generated OpenAPI JSON for {service_name}: {output_file}")
        return True
    except Exception as e:
        print(f"Error saving OpenAPI JSON for {service_name}: {e}")
        return False

def generate_redoc_html(service_name, openapi_file, output_dir):
    """Generate ReDoc HTML for a service."""
    redoc_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>{service_name.replace('-', ' ').title()} API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url="{openapi_file.name}"></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
</body>
</html>"""
    
    html_file = Path(output_dir) / f"{service_name}-redoc.html"
    
    try:
        with open(html_file, 'w') as f:
            f.write(redoc_template)
        print(f"Generated ReDoc HTML for {service_name}: {html_file}")
        return True
    except Exception as e:
        print(f"Error generating ReDoc HTML for {service_name}: {e}")
        return False

def main():
    """Main function to generate all API documentation."""
    # Create output directory
    docs_dir = Path(__file__).parent.parent / "docs" / "api"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    services = [
        ("text-summarization", generate_text_summarization_openapi),
        ("context-service", generate_context_service_openapi),
    ]
    
    success_count = 0
    
    for service_name, generator_func in services:
        print(f"\\nGenerating documentation for {service_name}...")
        
        # Generate OpenAPI JSON
        openapi_spec = generator_func()
        if save_openapi_json(service_name, openapi_spec, docs_dir):
            # Generate ReDoc HTML
            openapi_file = docs_dir / f"{service_name}-openapi.json"
            if generate_redoc_html(service_name, openapi_file, docs_dir):
                success_count += 1
    
    # Generate index page
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>MCP Platform API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .service {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        .service h2 {
            margin-top: 0;
            color: #007bff;
        }
        .links {
            margin-top: 10px;
        }
        .links a {
            display: inline-block;
            margin-right: 15px;
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
        }
        .links a:hover {
            background-color: #0056b3;
        }
        .json-link {
            background-color: #28a745 !important;
        }
        .json-link:hover {
            background-color: #1e7e34 !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MCP Platform API Documentation</h1>
        <p>Welcome to the MCP Platform API documentation. Below you'll find links to the interactive documentation for each service.</p>
        
        <div class="service">
            <h2>Text Summarization Service</h2>
            <p>AI-powered text summarization with semantic validation, JWT authentication, and comprehensive monitoring.</p>
            <div class="links">
                <a href="text-summarization-redoc.html">ReDoc Documentation</a>
                <a href="text-summarization-openapi.json" class="json-link">OpenAPI JSON</a>
            </div>
        </div>
        
        <div class="service">
            <h2>Context Service</h2>
            <p>Service for managing context data with tenant awareness, secure storage, and comprehensive API.</p>
            <div class="links">
                <a href="context-service-redoc.html">ReDoc Documentation</a>
                <a href="context-service-openapi.json" class="json-link">OpenAPI JSON</a>
            </div>
        </div>
        
        <div class="service">
            <h2>Development URLs</h2>
            <p>When running services locally in development mode:</p>
            <div class="links">
                <a href="http://localhost:8000/docs">Text Summarization - Swagger UI</a>
                <a href="http://localhost:8000/redoc">Text Summarization - ReDoc</a>
                <a href="http://localhost:8001/docs">Context Service - Swagger UI</a>
                <a href="http://localhost:8001/redoc">Context Service - ReDoc</a>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    index_file = docs_dir / "index.html"
    try:
        with open(index_file, 'w') as f:
            f.write(index_html)
        print(f"\\nGenerated API documentation index: {index_file}")
    except Exception as e:
        print(f"Error generating index file: {e}")
    
    print(f"\\nAPI documentation generation complete!")
    print(f"Successfully generated documentation for {success_count} services.")
    print(f"Documentation available in: {docs_dir}")
    print(f"Open {index_file} in your browser to view the documentation.")

if __name__ == "__main__":
    main()
