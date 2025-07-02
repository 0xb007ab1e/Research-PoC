# Contributing to the Project

Thank you for considering contributing to our project! We welcome contributions from everyone.

## Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```
2. **Install dependencies**
   ```bash
   ./install-dependencies.sh
   ```
3. **Ensure all tests pass**
   ```bash
   ./run-tests.sh
   ```

## Branching Strategy

We use the GitFlow branching strategy:
- **master**: contains production-ready code.
- **develop**: integration branch for new features.
- **feature/**: branches for developing new features.
- **release/**: prepare for a new release.
- **hotfix/**: emergency fixes.

## Commit Message Style

Follow this structure for commit messages:
- **type**: subject (max 50 characters)

  **Types**:
  - feat: A new feature
  - fix: A bug fix
  - docs: Documentation only changes
  - style: Changes that do not affect the meaning of the code (formatting)
  - refactor: A code change that neither fixes a bug nor adds a feature

## Code Review Checklist

- Ensure all code follows the coding standards.
- Write tests for new code.
- Review documentation updates.
- Validate that all tests pass.

## Testing Requirements

- **Unit Tests**: Required for all new code.
- **Integration Tests**: Test interactions between components.
- **Continuous Integration**: Ensures the code is validated and tested.

## Proposing Changes

1. Fork the repository and create your branch from `develop`.
2. Ensure all tests pass before opening a pull request.
3. Follow the pull request template and complete all items.

## Additional Resources

- [LICENSE](./LICENSE)

We appreciate your interest in contributing!
