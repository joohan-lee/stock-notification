# Development Workflow

## Python Project (uv)

** Always use `uv`, not `pip` **

```sh
# 1. Install dependencies
uv pip install -e ".[dev]"

# 2. Run tests
uv run pytest                       # All tests
uv run pytest -k "test name"        # Single test
uv run pytest tests/test_file.py    # Specific file

# 3. Type check (if configured)
uv run mypy src/

# 4. Lint (if configured)
uv run ruff check src/
uv run ruff format src/

# 5. Before creating PR
uv run pytest && uv run mypy src/
```

## Node.js Project (bun)

** Always use `bun`, not `npm` **

```sh
# 1. Make changes

# 2. Typecheck (fast)
bun run typecheck

# 3. Run tests
bun run test -- -t "test name"      # Single suite
bun run test:file -- "glob"         # Specific files

# 4. Lint before committing
bun run lint:file -- "file1.ts"     # Specific files
bun run lint                        # All files

# 5. Before creating PR
bun run lint:claude && bun run test
```

# Commit Convention

* Use conventional commit tags in commit messages
* Do NOT include `Co-Authored-By` in commit messages

| Tag | Description |
|-----|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Build, config, tooling changes |
| `style` | Formatting, whitespace (no logic change) |
| `perf` | Performance improvement |

Example: `feat: add daily change rule support`

# Rules
* Use English for all documentation, code comments.
