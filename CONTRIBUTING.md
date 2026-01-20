# Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Run code quality checks (`ruff check .`, `black --check .`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Quality Standards

This project uses:
- **Black** for code formatting (line length: 127)
- **Ruff** for linting
- **MyPy** for type checking (relaxed mode)
- **Pytest** for testing
- **Pre-commit hooks** for automated checks

Install pre-commit hooks:
```bash
./setup_precommit.sh
```
