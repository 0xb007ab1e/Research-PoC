# Requirements Mapping Tools Setup Guide

This guide explains how to set up the collaborative tools mentioned in the requirements gathering methodology.

## Miro Board Setup

### 1. Create Requirements Mapping Board

1. **Create New Board**: 
   - Go to [miro.com](https://miro.com)
   - Create a new board titled: "Multi-Tenant System Requirements Mapping"

2. **Board Structure**:
   ```
   |-- Stakeholder Swim Lanes --|
   | Business Requirements      |
   | Security Requirements      |
   | DevOps Requirements        |
   | Legal/Compliance Req.      |
   |-- Compliance Frameworks ---|
   | GDPR | SOC 2 | CCPA | ... |
   |-- Technical Architecture --|
   | Data Flow | Security Arch  |
   |-- Risk Assessment Matrix --|
   | High | Medium | Low Risk   |
   ```

3. **Stakeholder Swim Lanes**:
   - **Business Stakeholders**: Blue lane
     - Functional requirements
     - Performance targets
     - Business SLAs
   - **Security Team**: Red lane
     - Security controls
     - Threat model requirements
     - Compliance controls
   - **DevOps/SRE**: Green lane
     - Infrastructure requirements
     - Operational requirements
     - Monitoring needs
   - **Legal/Compliance**: Purple lane
     - Regulatory requirements
     - Data residency needs
     - Privacy controls

4. **Compliance Framework Overlay**:
   - GDPR section with Articles 6, 15, 16, 17, 20, 25, 28, 35
   - SOC 2 section with CC6, CC7, CC8, CC9, CC10
   - Regional compliance (CCPA, PIPEDA, etc.)

5. **Templates to Create**:
   - Requirement card template
   - Risk assessment template
   - Decision record template
   - Stakeholder feedback template

### 2. Collaboration Setup

1. **Invite Stakeholders**:
   - Share board with edit permissions
   - Create stakeholder-specific access if needed
   - Set up notification preferences

2. **Live Mapping Sessions**:
   - Schedule weekly requirements mapping sessions
   - Use Miro's video call integration
   - Record sessions for documentation

## GitHub Discussions Setup

### 1. Repository Setup

If you don't have a repository yet:
```bash
# Create new repository
gh repo create multi-tenant-requirements --public
cd multi-tenant-requirements
git init
git add 01-requirements.md
git commit -m "Initial requirements document"
git push -u origin main
```

### 2. Enable GitHub Discussions

1. Go to your repository settings
2. Scroll to "Features" section
3. Check "Discussions"
4. Configure discussion categories:

### 3. Discussion Categories

Create the following categories:

#### 📋 Requirements Q&A
- **Purpose**: Questions and clarifications about requirements
- **Template**:
  ```markdown
  ## Requirement ID
  [e.g., FR-001, NFR-002]
  
  ## Question
  [Clear, specific question about the requirement]
  
  ## Context
  [Background information, stakeholder source]
  
  ## Priority
  [High/Medium/Low]
  
  ## Stakeholder
  [Who needs this answered]
  ```

#### 🔒 Security & Compliance
- **Purpose**: Security and compliance-specific discussions
- **Template**:
  ```markdown
  ## Compliance Framework
  [GDPR, SOC 2, CCPA, etc.]
  
  ## Control/Article
  [Specific control or article reference]
  
  ## Question/Clarification
  [What needs to be clarified]
  
  ## Impact
  [How this affects the system design]
  ```

#### 🏗️ Technical Implementation
- **Purpose**: Technical feasibility and implementation discussions
- **Template**:
  ```markdown
  ## Requirement Reference
  [Link to requirement in 01-requirements.md]
  
  ## Technical Question
  [Specific technical question or concern]
  
  ## Proposed Solution
  [If applicable, proposed technical approach]
  
  ## Risks/Concerns
  [Technical risks or implementation concerns]
  ```

#### 📊 Business Logic
- **Purpose**: Business requirement clarifications
- **Template**:
  ```markdown
  ## Business Process
  [Which business process this relates to]
  
  ## Stakeholder
  [Business stakeholder involved]
  
  ## Question
  [Business logic question]
  
  ## Current State
  [How this works currently, if applicable]
  
  ## Desired State
  [How this should work in the new system]
  ```

#### 🎯 Decisions
- **Purpose**: Architecture and design decisions
- **Template**:
  ```markdown
  ## Decision Title
  [Short title of the decision]
  
  ## Status
  [Proposed/Accepted/Superseded]
  
  ## Context
  [What is the issue we're trying to solve]
  
  ## Options Considered
  [What alternatives did we consider]
  
  ## Decision
  [What we decided]
  
  ## Consequences
  [What are the consequences of this decision]
  ```

### 4. Discussion Management

#### Labels
Create labels for better organization:
- `priority-high`, `priority-medium`, `priority-low`
- `stakeholder-business`, `stakeholder-security`, `stakeholder-devops`, `stakeholder-legal`
- `compliance-gdpr`, `compliance-soc2`, `compliance-ccpa`
- `status-blocked`, `status-in-review`, `status-resolved`

#### Automated Workflows
Create `.github/workflows/discussion-automation.yml`:
```yaml
name: Discussion Automation
on:
  discussion:
    types: [created, answered]

jobs:
  auto-label:
    runs-on: ubuntu-latest
    steps:
      - name: Auto-label discussions
        uses: actions/github-script@v6
        with:
          script: |
            const title = context.payload.discussion.title.toLowerCase();
            const labels = [];
            
            if (title.includes('gdpr')) labels.push('compliance-gdpr');
            if (title.includes('soc2') || title.includes('soc 2')) labels.push('compliance-soc2');
            if (title.includes('security')) labels.push('stakeholder-security');
            if (title.includes('business')) labels.push('stakeholder-business');
            
            if (labels.length > 0) {
              await github.rest.issues.addLabels({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.payload.discussion.number,
                labels: labels
              });
            }
```

### 5. Export to Markdown

Create a script to export discussions to markdown:
```bash
#!/bin/bash
# export-discussions.sh

echo "# Requirements Discussions Export"
echo "Generated: $(date)"
echo

gh api repos/:owner/:repo/discussions --paginate | \
jq -r '.[] | "## \(.title)\n**Category:** \(.category.name)\n**Author:** \(.user.login)\n**Created:** \(.created_at)\n\n\(.body)\n\n---\n"'
```

## Integration with Requirements Document

### 1. Link Discussions to Requirements
In your `01-requirements.md`, add discussion links:
```markdown
| FR-001 | Multi-tenant data isolation | Critical | Security | [Discussion #1](link) | Complete logical separation |
```

### 2. Weekly Sync Process
1. Export discussions to markdown
2. Update requirements document with clarifications
3. Update Miro board with new requirements
4. Create summary report for stakeholders

### 3. Traceability Matrix
Create a traceability matrix linking:
- Requirements → Discussions → Decisions → Implementation

## Best Practices

### Miro Best Practices
1. Use consistent color coding
2. Keep cards concise but detailed
3. Use linking to show relationships
4. Regular board cleanup and organization
5. Screenshot important sessions

### GitHub Discussions Best Practices
1. Use clear, descriptive titles
2. Reference specific requirements by ID
3. Close resolved discussions promptly
4. Use @mentions to notify stakeholders
5. Pin important discussions

### General Best Practices
1. Weekly stakeholder sync meetings
2. Export and backup discussions regularly
3. Maintain single source of truth in requirements doc
4. Use both tools complementarily (live collaboration in Miro, async in GitHub)
5. Regular tool hygiene and organization
