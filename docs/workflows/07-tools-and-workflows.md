# Tools, Workflows & Agents Guide

This guide covers the essential tools, workflows, and intelligent agents that power modern software development, from code analysis to AI-assisted development and collaboration.

## Code Analysis

### Static Analysis Tools

#### Ruff (Python)
```bash
# Install ruff
pip install ruff

# Basic linting
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Generate SARIF output for GitHub Code Scanning
ruff check --output-format=sarif > ruff-results.sarif
```

**Configuration (.ruff.toml):**
```toml
[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "T20"]
ignore = ["E501"]  # Line too long

[tool.ruff.isort]
known-first-party = ["myproject"]
```

#### golangci-lint (Go)
```bash
# Install golangci-lint
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v1.54.2

# Run analysis
golangci-lint run

# Generate SARIF output
golangci-lint run --out-format sarif > golangci-results.sarif
```

**Configuration (.golangci.yml):**
```yaml
run:
  timeout: 5m
  modules-download-mode: readonly

linters:
  enable:
    - gofmt
    - goimports
    - govet
    - ineffassign
    - misspell
    - staticcheck
    - unused
    - errcheck

linters-settings:
  goimports:
    local-prefixes: github.com/myorg/myproject
```

#### Cargo Clippy (Rust)
```bash
# Install clippy
rustup component add clippy

# Run clippy
cargo clippy

# Run with all targets
cargo clippy --all-targets --all-features

# Generate JSON output for SARIF conversion
cargo clippy --message-format=json > clippy-results.json

# Convert to SARIF (using clippy-sarif tool)
cargo install clippy-sarif sarif-fmt
cargo clippy --message-format=json | clippy-sarif | sarif-fmt > clippy-results.sarif
```

**Configuration (clippy.toml):**
```toml
# Clippy configuration
avoid-breaking-exported-api = false
msrv = "1.70.0"

# Custom lints
disallowed-methods = [
    { path = "std::collections::HashMap::new", reason = "use ahash::HashMap instead" }
]
```

### GitHub Code Scanning Integration

**GitHub Actions Workflow (.github/workflows/code-scanning.yml):**
```yaml
name: Code Scanning

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  analyze:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        language: [python, go, rust]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      if: matrix.language == 'python'
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Setup Go
      if: matrix.language == 'go'
      uses: actions/setup-go@v4
      with:
        go-version: '1.21'
    
    - name: Setup Rust
      if: matrix.language == 'rust'
      uses: actions-rs/toolchain@v1
      with:
        toolchain: stable
        components: clippy
    
    - name: Run Python Analysis
      if: matrix.language == 'python'
      run: |
        pip install ruff
        ruff check --output-format=sarif > ruff-results.sarif
    
    - name: Run Go Analysis
      if: matrix.language == 'go'
      run: |
        curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin
        golangci-lint run --out-format sarif > golangci-results.sarif
    
    - name: Run Rust Analysis
      if: matrix.language == 'rust'
      run: |
        cargo install clippy-sarif sarif-fmt
        cargo clippy --message-format=json | clippy-sarif | sarif-fmt > clippy-results.sarif
    
    - name: Upload SARIF results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: ${{ matrix.language }}-results.sarif
```

## Development Workflows

### Trunk-Based Development

#### Feature Flags with Unleash

**Setup:**
```bash
# Install Unleash SDK
npm install unleash-client  # Node.js
pip install UnleashClient   # Python
go get github.com/Unleash/unleash-client-go/v3  # Go
```

**Usage Example (Python):**
```python
from UnleashClient import UnleashClient

client = UnleashClient(
    url="https://unleash.company.com/api/",
    app_name="my-python-app",
    custom_headers={'Authorization': 'Bearer <token>'}
)

client.initialize_client()

# Feature flag usage
if client.is_enabled("new-checkout-flow"):
    # New feature implementation
    process_checkout_v2()
else:
    # Fallback to existing implementation
    process_checkout_v1()
```

**Unleash Strategy Configuration:**
```json
{
  "name": "new-checkout-flow",
  "description": "New checkout flow with improved UX",
  "enabled": true,
  "strategies": [
    {
      "name": "gradualRolloutUserId",
      "parameters": {
        "percentage": "25",
        "groupId": "checkout-flow"
      }
    }
  ]
}
```

### Conventional Commits & Semantic Release

#### Conventional Commits Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Examples:**
```
feat: add user authentication system
fix(api): resolve timeout issues in payment processing
docs: update API documentation for v2.0
chore(deps): bump lodash from 4.17.19 to 4.17.21
BREAKING CHANGE: API v1 endpoints are now deprecated
```

#### Semantic Release Configuration

**package.json:**
```json
{
  "devDependencies": {
    "@semantic-release/changelog": "^6.0.3",
    "@semantic-release/git": "^10.0.1",
    "@semantic-release/github": "^9.0.4",
    "semantic-release": "^21.0.7"
  },
  "release": {
    "branches": ["main"],
    "plugins": [
      "@semantic-release/commit-analyzer",
      "@semantic-release/release-notes-generator",
      "@semantic-release/changelog",
      "@semantic-release/npm",
      "@semantic-release/github",
      [
        "@semantic-release/git",
        {
          "assets": ["CHANGELOG.md", "package.json"],
          "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
        }
      ]
    ]
  }
}
```

**GitHub Actions (.github/workflows/release.yml):**
```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
        token: ${{ secrets.GH_TOKEN }}
    
    - uses: actions/setup-node@v4
      with:
        node-version: '18'
    
    - run: npm ci
    
    - run: npx semantic-release
      env:
        GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
        NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## AI/ML Context Tools

### LangChain Server for Retrieval Models

**Server Setup:**
```python
from fastapi import FastAPI
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import PGVector
from langchain.llms import OpenAI
import os

app = FastAPI()

# Initialize embeddings and vector store
embeddings = OpenAIEmbeddings()
connection_string = PGVector.connection_string_from_db_params(
    driver=os.getenv("PGVECTOR_DRIVER", "psycopg2"),
    host=os.getenv("PGVECTOR_HOST", "localhost"),
    port=int(os.getenv("PGVECTOR_PORT", "5432")),
    database=os.getenv("PGVECTOR_DATABASE", "vectordb"),
    user=os.getenv("PGVECTOR_USER", "postgres"),
    password=os.getenv("PGVECTOR_PASSWORD", "")
)

vectorstore = PGVector(
    connection_string=connection_string,
    embedding_function=embeddings,
    collection_name="documents"
)

# Create retrieval chain
llm = OpenAI(temperature=0)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 4})
)

@app.post("/query")
async def query_documents(query: str):
    """Query the document retrieval system"""
    response = qa_chain.run(query)
    return {"response": response}

@app.post("/add_documents")
async def add_documents(documents: list[str]):
    """Add new documents to the vector store"""
    vectorstore.add_texts(documents)
    return {"status": "Documents added successfully"}
```

### PGVector Embedding Storage

**Database Setup:**
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table
CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for similarity search
CREATE INDEX ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Example similarity search
SELECT content, metadata, 
       1 - (embedding <=> '[0.1, 0.2, 0.3, ...]') AS similarity
FROM document_embeddings
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'
LIMIT 5;
```

### HuggingFace Spaces Fine-tuning Pipeline

**Spaces Configuration (app.py):**
```python
import gradio as gr
import wandb
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import TrainingArguments, Trainer
import torch

# Initialize W&B for cost tracking
wandb.init(
    project="model-finetuning",
    config={
        "model_name": "bert-base-uncased",
        "learning_rate": 2e-5,
        "batch_size": 16,
        "num_epochs": 3
    }
)

def fine_tune_model(dataset_file, model_name, learning_rate, epochs):
    """Fine-tune a model with cost tracking"""
    
    # Log training start
    wandb.log({"training_status": "started"})
    
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    
    # Training arguments with cost tracking
    training_args = TrainingArguments(
        output_dir="./results",
        learning_rate=float(learning_rate),
        per_device_train_batch_size=16,
        num_train_epochs=int(epochs),
        logging_strategy="steps",
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="epoch",
        report_to="wandb"  # Enable W&B logging
    )
    
    # Calculate estimated costs
    estimated_cost = calculate_training_cost(epochs, len(dataset))
    wandb.log({"estimated_cost_usd": estimated_cost})
    
    # Training loop would go here
    # trainer = Trainer(...)
    # trainer.train()
    
    wandb.log({"training_status": "completed"})
    
    return f"Model fine-tuned successfully. Estimated cost: ${estimated_cost:.2f}"

def calculate_training_cost(epochs, dataset_size):
    """Calculate estimated training cost"""
    # Rough estimation based on compute hours
    compute_hours = (epochs * dataset_size) / 1000  # Simplified calculation
    cost_per_hour = 0.50  # Example cost per GPU hour
    return compute_hours * cost_per_hour

# Gradio interface
interface = gr.Interface(
    fn=fine_tune_model,
    inputs=[
        gr.File(label="Training Dataset"),
        gr.Dropdown(["bert-base-uncased", "roberta-base"], label="Base Model"),
        gr.Slider(1e-5, 1e-3, value=2e-5, label="Learning Rate"),
        gr.Slider(1, 10, value=3, step=1, label="Epochs")
    ],
    outputs="text",
    title="Model Fine-tuning Pipeline",
    description="Fine-tune transformer models with automatic cost tracking via W&B"
)

if __name__ == "__main__":
    interface.launch()
```

## Collaboration

### GitHub Projects Integration

**Automated PR Linking Script:**
```python
import requests
import re
from github import Github

class GitHubProjectManager:
    def __init__(self, token, org, project_number):
        self.github = Github(token)
        self.org = org
        self.project_number = project_number
        
    def link_pr_to_project(self, pr_number, repo_name):
        """Automatically link PR to project based on labels or keywords"""
        
        repo = self.github.get_repo(f"{self.org}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        # Extract project items from PR description or title
        project_keywords = self._extract_project_keywords(pr.title, pr.body)
        
        if project_keywords:
            self._add_pr_to_project(pr, project_keywords)
    
    def _extract_project_keywords(self, title, body):
        """Extract project-related keywords from PR"""
        text = f"{title} {body}".lower()
        
        # Look for issue references, feature tags, etc.
        patterns = [
            r'#(\d+)',  # Issue numbers
            r'feat:\s*(\w+)',  # Feature labels
            r'fix:\s*(\w+)',   # Fix labels
        ]
        
        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        return keywords
    
    def _add_pr_to_project(self, pr, keywords):
        """Add PR to appropriate project column"""
        # GitHub GraphQL API call to add PR to project
        # Implementation would use GitHub's Projects API
        pass

# GitHub Actions webhook handler
@app.post("/webhook/pr")
async def handle_pr_webhook(payload: dict):
    """Handle PR events and auto-link to projects"""
    
    if payload["action"] == "opened":
        pr_number = payload["pull_request"]["number"]
        repo_name = payload["repository"]["full_name"]
        
        manager = GitHubProjectManager(
            token=os.getenv("GITHUB_TOKEN"),
            org="myorg",
            project_number=1
        )
        
        manager.link_pr_to_project(pr_number, repo_name)
    
    return {"status": "processed"}
```

### Slack Integration with tldr; ChatGPT Plugin

**Slack Bot for PR Summaries:**
```python
import openai
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import difflib

class PRSummarizer:
    def __init__(self, slack_token, openai_api_key):
        self.slack_client = WebClient(token=slack_token)
        openai.api_key = openai_api_key
    
    def summarize_pr_diff(self, pr_diff):
        """Generate tldr; summary of PR diff using ChatGPT"""
        
        prompt = f"""
        Please provide a concise tldr; summary of this pull request diff:
        
        {pr_diff}
        
        Focus on:
        - What changed
        - Why it changed
        - Impact on users/system
        
        Keep it under 3 sentences.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a technical writer specializing in concise code change summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    def post_pr_summary(self, pr_data, diff_text):
        """Post PR summary to Slack #mcp-review channel"""
        
        summary = self.summarize_pr_diff(diff_text)
        
        message = {
            "channel": "#mcp-review",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*New PR Ready for Review*\n<{pr_data['url']}|{pr_data['title']}>"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*tldr;* {summary}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Author: {pr_data['author']} | Files changed: {pr_data['files_changed']} | +{pr_data['additions']} -{pr_data['deletions']}"
                        }
                    ]
                }
            ]
        }
        
        try:
            self.slack_client.chat_postMessage(**message)
        except SlackApiError as e:
            print(f"Error posting to Slack: {e}")

# Webhook handler for GitHub PR events
@app.post("/webhook/pr-review")
async def handle_pr_review(payload: dict):
    """Handle PR ready for review events"""
    
    if payload["action"] == "ready_for_review":
        pr = payload["pull_request"]
        
        # Fetch PR diff
        diff_response = requests.get(pr["diff_url"])
        diff_text = diff_response.text
        
        pr_data = {
            "url": pr["html_url"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "files_changed": pr["changed_files"],
            "additions": pr["additions"],
            "deletions": pr["deletions"]
        }
        
        summarizer = PRSummarizer(
            slack_token=os.getenv("SLACK_TOKEN"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        summarizer.post_pr_summary(pr_data, diff_text)
    
    return {"status": "processed"}
```

## Agents

### Semantic-Kernel Plugin Agent for API Examples

**Plugin Configuration:**
```python
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

class APIExampleGenerator:
    def __init__(self, openai_api_key):
        self.kernel = sk.Kernel()
        
        # Add OpenAI service
        self.kernel.add_chat_service(
            "openai",
            OpenAIChatCompletion("gpt-4", openai_api_key)
        )
        
        # Define the plugin function
        self.example_function = self.kernel.create_semantic_function(
            function_definition="""
            Generate a comprehensive API usage example for the following endpoint:
            
            Endpoint: {{$endpoint}}
            Method: {{$method}}
            Description: {{$description}}
            Parameters: {{$parameters}}
            
            Please provide:
            1. A complete code example in Python
            2. A complete code example in JavaScript
            3. Example request/response JSON
            4. Common error handling scenarios
            
            Make the examples production-ready with proper error handling.
            """,
            function_name="generate_api_example",
            max_tokens=1500,
            temperature=0.2
        )
    
    async def generate_examples(self, api_spec):
        """Generate API examples from OpenAPI specification"""
        
        examples = {}
        
        for path, methods in api_spec["paths"].items():
            for method, details in methods.items():
                
                context = sk.ContextVariables()
                context["endpoint"] = path
                context["method"] = method.upper()
                context["description"] = details.get("summary", "")
                context["parameters"] = str(details.get("parameters", []))
                
                result = await self.example_function.invoke_async(context=context)
                
                examples[f"{method.upper()} {path}"] = result.result
        
        return examples
    
    def save_examples_to_docs(self, examples, output_dir):
        """Save generated examples to documentation files"""
        
        import os
        import json
        
        for endpoint, example in examples.items():
            filename = endpoint.replace(" ", "_").replace("/", "_")
            filepath = os.path.join(output_dir, f"{filename}_example.md")
            
            with open(filepath, "w") as f:
                f.write(f"# {endpoint} API Example\n\n")
                f.write(example)

# Usage
async def main():
    generator = APIExampleGenerator(os.getenv("OPENAI_API_KEY"))
    
    # Load OpenAPI spec
    with open("api-spec.json", "r") as f:
        api_spec = json.load(f)
    
    # Generate examples
    examples = await generator.generate_examples(api_spec)
    
    # Save to documentation
    generator.save_examples_to_docs(examples, "./docs/examples")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### OpenAI Function-Calling Agent for Code Review

**Code Review Agent:**
```python
import openai
import ast
import json
from typing import List, Dict

class CodeReviewAgent:
    def __init__(self, openai_api_key):
        openai.api_key = openai_api_key
        
        self.functions = [
            {
                "name": "suggest_improvement",
                "description": "Suggest a code improvement with specific line numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "line_start": {"type": "integer"},
                        "line_end": {"type": "integer"},
                        "issue_type": {
                            "type": "string",
                            "enum": ["performance", "security", "maintainability", "bug", "style"]
                        },
                        "description": {"type": "string"},
                        "suggested_code": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"]
                        }
                    },
                    "required": ["file_path", "line_start", "line_end", "issue_type", "description", "severity"]
                }
            }
        ]
    
    def review_pr_diff(self, diff_content: str) -> List[Dict]:
        """Review PR diff and generate inline suggestions"""
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert code reviewer. Analyze the provided diff and suggest improvements.
                Focus on:
                - Security vulnerabilities
                - Performance issues
                - Code maintainability
                - Potential bugs
                - Style inconsistencies
                
                Use the suggest_improvement function for each issue you find."""
            },
            {
                "role": "user",
                "content": f"Please review this PR diff:\n\n{diff_content}"
            }
        ]
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            functions=self.functions,
            function_call="auto",
            temperature=0.2
        )
        
        suggestions = []
        
        # Process function calls
        if response.choices[0].message.get("function_call"):
            function_call = response.choices[0].message["function_call"]
            if function_call["name"] == "suggest_improvement":
                suggestion = json.loads(function_call["arguments"])
                suggestions.append(suggestion)
        
        return suggestions
    
    def post_inline_comments(self, suggestions: List[Dict], pr_number: int, repo: str):
        """Post inline comments to GitHub PR"""
        
        from github import Github
        
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo_obj = g.get_repo(repo)
        pr = repo_obj.get_pull(pr_number)
        
        for suggestion in suggestions:
            comment_body = f"""## {suggestion['issue_type'].title()} Issue (Severity: {suggestion['severity']})

{suggestion['description']}

### Suggested Improvement:
```python
{suggestion.get('suggested_code', 'See description above')}
```

*This comment was generated by an AI code review agent.*"""
            
            try:
                pr.create_review_comment(
                    body=comment_body,
                    commit=pr.get_commits().reversed[0],
                    path=suggestion['file_path'],
                    line=suggestion['line_end']
                )
            except Exception as e:
                print(f"Error posting comment: {e}")

# GitHub Actions integration
@app.post("/webhook/code-review")
async def trigger_code_review(payload: dict):
    """Trigger automated code review on PR"""
    
    if payload["action"] == "opened" or payload["action"] == "synchronize":
        pr_number = payload["pull_request"]["number"]
        repo_name = payload["repository"]["full_name"]
        
        # Fetch PR diff
        diff_url = payload["pull_request"]["diff_url"]
        diff_response = requests.get(diff_url)
        diff_content = diff_response.text
        
        # Run code review
        reviewer = CodeReviewAgent(os.getenv("OPENAI_API_KEY"))
        suggestions = reviewer.review_pr_diff(diff_content)
        
        # Post suggestions as inline comments
        reviewer.post_inline_comments(suggestions, pr_number, repo_name)
    
    return {"status": "review_completed"}
```

## Integration Workflows

### Complete CI/CD Pipeline Integration

**GitHub Actions Workflow (.github/workflows/full-pipeline.yml):**
```yaml
name: Full Development Pipeline

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Code Analysis
      run: |
        # Run all static analysis tools
        ruff check --output-format=sarif > ruff-results.sarif
        golangci-lint run --out-format sarif > golangci-results.sarif
        cargo clippy --message-format=json | clippy-sarif | sarif-fmt > clippy-results.sarif
    
    - name: Upload SARIF
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: ./*-results.sarif
  
  ai-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
    - name: Trigger AI Code Review
      run: |
        curl -X POST "${{ secrets.REVIEW_WEBHOOK_URL }}" \
          -H "Content-Type: application/json" \
          -d '${{ toJson(github.event) }}'
  
  feature-flags:
    runs-on: ubuntu-latest
    steps:
    - name: Update Feature Flags
      run: |
        # Update Unleash feature flags based on deployment
        curl -X POST "${{ secrets.UNLEASH_API_URL }}/api/admin/projects/default/features" \
          -H "Authorization: Bearer ${{ secrets.UNLEASH_TOKEN }}" \
          -H "Content-Type: application/json" \
          -d '{"name": "deployment-${{ github.sha }}", "enabled": true}'
  
  release:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [analyze, feature-flags]
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
        token: ${{ secrets.GH_TOKEN }}
    
    - name: Semantic Release
      run: npx semantic-release
      env:
        GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
        SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
```

This comprehensive guide provides the foundation for modern development workflows with integrated AI assistance, automated analysis, and intelligent collaboration tools.
