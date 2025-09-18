# Contributing to Savior

First off, thanks for taking the time to contribute! 🛟

## How Can I Contribute?

### Reporting Bugs
- Use the issue tracker
- Describe what you expected vs what happened
- Include your OS and Python version

### Suggesting Features
- Check if it's already suggested
- Keep it simple - Savior should stay dead simple
- Explain the use case

### Pull Requests
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Write tests for your changes
4. Run the test suite (`pytest`)
5. Commit with a descriptive message
6. Push to your fork
7. Open a Pull Request

### Code Style
- Use Black for formatting: `black savior tests`
- Keep functions small and focused
- Add docstrings for new functions
- No unnecessary complexity

### Philosophy
Remember: Savior is meant to be **dead simple**. Features should:
- Work out of the box
- Require minimal configuration
- Not surprise users
- Be self-hosted/privacy-first

### Testing
```bash
# Run tests
pytest

# With coverage
pytest --cov=savior

# Run specific test
pytest tests/test_zombie.py
```

### Questions?
Open an issue! We're friendly 😊