# GitHub CLI Integration

This documentation describes how to integrate GitHub CLI within the MCP Platform project, covering installation options, authentication methods, script usage examples, Make targets, and security best practices.

## Overview

The MCP Platform includes GitHub CLI integration through Docker containers and Make targets to facilitate CI/CD operations, repository management, and automated workflows. The integration supports both interactive development and automated CI/CD environments.

## Installation Options

### Local Installation

#### macOS
```bash
# Using Homebrew
brew install gh

# Verify installation
gh --version
```

#### Linux (Debian/Ubuntu)
```bash
# Add GitHub CLI repository
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

# Install GitHub CLI
sudo apt update && sudo apt install gh

# Verify installation
gh --version
```

#### Windows
Download and install from the [GitHub CLI releases page](https://github.com/cli/cli/releases).

### Docker-based Installation

The project includes a pre-configured Docker container with GitHub CLI:

```bash
# Start GitHub CLI service container
make gh-cli-up

# Access interactive shell
docker exec -it mcp-gh-cli-dev bash

# Run commands directly
docker-compose -f docker-compose.dev.yml exec gh-cli gh --help
```

### Automated Installation via Make

```bash
# Install GitHub CLI automatically (detects environment)
make gh-install
```

This target automatically:
- Detects if running inside Docker or on host
- Installs appropriate packages for the environment
- Verifies successful installation

## Authentication Methods

### Device Flow Authentication

**Best for:** Interactive development environments with browser access.

```bash
# Interactive device flow (opens browser)
make gh-login

# Manual device flow
gh auth login --web
```

**Process:**
1. Command opens browser to GitHub device activation page
2. Enter the displayed code
3. Authorize the application
4. Authentication token is stored locally

### Personal Access Token (PAT) Authentication

**Best for:** CI/CD environments, automation, headless environments.

#### Using Environment Variable
```bash
# Set token as environment variable
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Authenticate using token
make gh-login
```

#### Using Token File
```bash
# Store token in file (secure method)
echo "ghp_xxxxxxxxxxxxxxxxxxxx" | gh auth login --with-token
```

#### CI/CD Integration
```yaml
# Example GitHub Actions workflow
- name: Authenticate GitHub CLI
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    echo "$GITHUB_TOKEN" | gh auth login --with-token
```

### SSH Key Authentication

```bash
# Configure SSH-based authentication
gh auth login --git-protocol ssh
```

## Script Usage Examples

### Repository Operations

```bash
# Clone repository with GitHub CLI
gh repo clone owner/repository

# Create new repository
gh repo create my-new-repo --public --description "My new repository"

# Fork repository
gh repo fork owner/repository

# View repository information
gh repo view owner/repository
```

### Issue Management

```bash
# List issues
gh issue list

# Create new issue
gh issue create --title "Bug report" --body "Description of the bug"

# View specific issue
gh issue view 123

# Close issue
gh issue close 123
```

### Pull Request Operations

```bash
# Create pull request
gh pr create --title "Feature: Add new functionality" --body "Detailed description"

# List pull requests
gh pr list

# Review pull request
gh pr review 456 --approve

# Merge pull request
gh pr merge 456 --merge
```

### Release Management

```bash
# Create new release
gh release create v1.0.0 --title "Release v1.0.0" --notes "Release notes"

# List releases
gh release list

# Upload assets to release
gh release upload v1.0.0 ./dist/binary.tar.gz
```

### Workflow Operations

```bash
# List workflow runs
gh run list

# View specific workflow run
gh run view 123456

# Re-run failed workflow
gh run rerun 123456
```

## Make Targets

The project includes several Make targets for GitHub CLI operations:

### Core Targets

| Target | Description | Usage |
|--------|-------------|-------|
| `gh-install` | Installs GitHub CLI locally or in container | `make gh-install` |
| `gh-login` | Authenticates with GitHub CLI | `make gh-login` |
| `gh-cli-up` | Starts GitHub CLI Docker service | `make gh-cli-up` |

### Usage Examples

```bash
# Complete setup and authentication flow
make gh-install    # Install GitHub CLI
make gh-cli-up     # Start Docker service
make gh-login      # Authenticate

# Direct command execution
docker-compose -f docker-compose.dev.yml exec gh-cli gh repo list

# Interactive shell access
docker exec -it mcp-gh-cli-dev bash
```

### Integration with CI/CD Pipeline

```bash
# Example CI pipeline integration
make gh-install                           # Install CLI
export GITHUB_TOKEN="$CI_GITHUB_TOKEN"    # Set token
make gh-login                             # Authenticate
gh release create v1.0.0 --auto          # Create release
```

## Security Best Practices

### Token Management

#### Never Commit Secrets
```bash
# ✅ Good: Use environment variables
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# ❌ Bad: Never do this
# git commit -m "Add GitHub token: ghp_xxxxxxxxxxxxxxxxxxxx"
```

#### Secure Token Storage
```bash
# Use secure environment variable management
# In production, use secret management systems like:
# - HashiCorp Vault
# - AWS Secrets Manager  
# - Azure Key Vault
# - Kubernetes Secrets

# Local development: use dotenv files (add to .gitignore)
echo "GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx" > .env.local
echo ".env.local" >> .gitignore
```

#### Token Rotation
```bash
# Regular token rotation (recommended every 90 days)
gh auth token  # View current token info
gh auth refresh  # Refresh token if supported
```

### Permission Management

#### Principle of Least Privilege
When creating Personal Access Tokens, only grant necessary scopes:

**Minimal scopes for common operations:**
- Repository operations: `repo` scope
- Public repository access: `public_repo` scope  
- Issue management: `repo` or `public_repo` scope
- Package registry: `read:packages`, `write:packages`

#### Scope Examples
```bash
# Creating tokens with specific scopes
# Via GitHub web interface, select only:
# ✅ repo (for private repos) OR public_repo (for public repos only)
# ✅ workflow (for GitHub Actions)
# ✅ write:packages (for package registry)
# ❌ Avoid: admin:org, delete_repo, admin:repo_hook
```

### Environment Security

#### Container Security
```bash
# Run containers with non-root user
docker run --user 1000:1000 github-cli-tools

# Use read-only filesystems where possible
docker run --read-only github-cli-tools

# Limit container capabilities
docker run --cap-drop ALL github-cli-tools
```

#### Network Security
```bash
# Use specific network configurations
docker network create --driver bridge secure-gh-network
docker run --network secure-gh-network github-cli-tools
```

### Monitoring and Auditing

#### Audit Token Usage
```bash
# Regular audit of token usage
gh api user  # Verify token is working
gh auth status  # Check authentication status

# Monitor API rate limits
gh api rate_limit
```

#### Activity Monitoring
- Enable GitHub security alerts
- Monitor unusual API activity
- Regular review of authorized applications
- Set up notifications for new device logins

### General Security Guidelines

1. **Keep Software Updated**
   ```bash
   # Regular updates
   brew upgrade gh  # macOS
   sudo apt update && sudo apt upgrade gh  # Linux
   ```

2. **Secure Configuration**
   ```bash
   # Set secure defaults
   gh config set editor "vim"
   gh config set git_protocol "ssh"
   gh config set prompt "enabled"
   ```

3. **Access Control**
   ```bash
   # Use organization-level access controls
   # Configure branch protection rules
   # Enable required status checks
   # Require pull request reviews
   ```

4. **Regular Security Reviews**
   - Monthly review of active tokens
   - Quarterly security assessment
   - Annual access control audit
   - Monitor GitHub security advisories

### Incident Response

If a token is compromised:

1. **Immediate Actions**
   ```bash
   # Revoke the compromised token immediately
   # Via GitHub web interface: Settings > Developer settings > Personal access tokens
   
   # Generate new token with minimal required scopes
   # Update CI/CD systems with new token
   ```

2. **Assessment**
   - Review recent API activity
   - Check for unauthorized repository access
   - Verify no malicious commits or releases

3. **Recovery**
   - Update all systems with new token
   - Test all integrations
   - Document incident for future reference

