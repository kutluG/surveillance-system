# Contributing to Surveillance System

Thank you for considering contributing to the Surveillance System! We welcome enhancements, bug fixes, new services, and documentation improvements.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/surveillance-system.git
   cd surveillance-system
   ```
3. Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```
4. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```

## Development Workflow

- Follow the Gitflow or GitHub Flow strategy:
  - `main` is always production-ready.
  - Create short-lived feature branches off `main`.
  - Open a pull request when your feature is ready.

- Ensure linting, formatting, and tests pass locally:
  ```bash
  make lint
  make test
  ```

- Update documentation in the `/docs` folder as needed.

## Code Standards

- Python code must follow Black, isort, Flake8, and mypy rules (enforced by pre-commit).
- JavaScript/TypeScript must follow ESLint rules.
- Write unit and integration tests for new functionality.

## Pull Request Guidelines

- Describe the purpose of your change clearly in the PR description.
- Link any related issues.
- Include relevant changelog entries if applicable.
- Request reviews from at least one teammate.

## Code Reviews

- Reviewers will focus on correctness, readability, and tests.
- Address review comments promptly.

## Thank You

We appreciate your contribution! 🎉
