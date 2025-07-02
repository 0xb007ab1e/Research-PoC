# GitHub CLI Tooling

This directory contains tooling and utilities for working with GitHub CLI (`gh`) in containerized environments.

## Purpose

This tooling provides:
- A lightweight Docker image with GitHub CLI pre-installed
- Helper scripts for common GitHub operations
- Standardized environment for GitHub CLI workflows

## Prerequisites

### Local Development
- Docker installed and running
- GitHub CLI (`gh`) installed locally (optional, for local development)
- Valid GitHub authentication token or SSH key

### Docker Usage
- Docker installed and running
- Access to build Docker images

## Directory Structure

```
tools/github-cli/
├── Dockerfile          # Lightweight Alpine-based image with gh CLI
├── README.md           # This documentation
└── scripts/            # Helper scripts for GitHub operations
```

## Usage

### Building the Docker Image

```bash
cd tools/github-cli
docker build -t github-cli-tools .
```

### Running the Container

```bash
# Interactive shell
docker run -it --rm github-cli-tools

# Mount current directory and run with GitHub token
docker run -it --rm \
  -v $(pwd):/workspace \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  github-cli-tools
```

### Authentication

The container expects GitHub authentication via:
1. Environment variable: `GITHUB_TOKEN`
2. SSH key mounted to the container
3. GitHub CLI config directory mounted to the container

## Scripts

The `scripts/` directory will contain helper scripts for:
- Repository operations
- Issue and PR management
- Workflow automation
- Release management

## Contributing

When adding new scripts:
1. Place them in the `scripts/` directory
2. Use `.sh` extension for shell scripts
3. Use `.py` extension for Python scripts
4. Ensure scripts are executable
5. Update this README with script descriptions

## Security Notes

- Never commit GitHub tokens to version control
- Use environment variables or mounted secrets for authentication
- Regularly rotate access tokens
- Follow principle of least privilege for token scopes
