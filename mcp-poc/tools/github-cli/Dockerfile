# GitHub CLI Tooling Docker Image
# Based on Alpine Linux for lightweight deployment

FROM alpine:latest

# Install dependencies and GitHub CLI
RUN apk update && \
    apk add --no-cache \
        git \
        curl \
        bash \
        jq \
        openssh-client && \
    # Install GitHub CLI
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null || true && \
    # For Alpine, use direct binary installation
    curl -sSL https://github.com/cli/cli/releases/latest/download/gh_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/').tar.gz | \
    tar -xz -C /tmp && \
    mv /tmp/gh_*/bin/gh /usr/local/bin/ && \
    rm -rf /tmp/gh_*

# Set working directory
WORKDIR /workspace

# Copy scripts directory
COPY scripts/ /workspace/scripts/

# Make scripts executable
RUN find /workspace/scripts -name "*.sh" -exec chmod +x {} \;

# Default command
CMD ["/bin/bash"]
