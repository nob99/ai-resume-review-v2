# Repository Guidelines

Use this guide alongside the high-level overview in [`README.md`](README.md) when onboarding or planning larger changes.

## Project Structure & Module Organization
- `frontend/` hosts the Next.js app; feature slices live under `src/features`, reusable UI in `src/components`, and routing/layout in `src/app`.
- `backend/` exposes the FastAPI service; each domain lives in `app/features/*`, shared infra in `app/core`, and AI pipelines in `ai_agents/`.
- Data and infra assets reside in `database/`, `config/`, `terraform/`, and automation scripts under `scripts/`; Docker orchestration sits in `docker-compose.dev.yml`.

## Build, Test, and Development Commands
- `./scripts/docker/dev.sh up` boots the full stack; pair with `status` or `logs <service>` for health checks.
- `cd frontend && npm run dev` serves Next.js locally; `npm run build` emits production bundles.
- `cd backend && uvicorn app.main:app --reload` runs the API without Docker; `pip install -r requirements.txt` prepares dependencies.
- Run `npm run lint`, `npm run test[:coverage]`, and `pytest` or `pytest -m "not integration"` before pushing; invoke them inside containers with `./scripts/docker/dev.sh shell <service>` when Dockerized.

## Coding Style & Naming Conventions
- TypeScript/React code follows the Next.js ESLint rules; keep 2-space indent, title components with PascalCase, hooks/utilities in camelCase, and suffix tests with `.test.ts[x]`.
- Python relies on `black` (line length 88), `isort`, `flake8`, and `mypy`; prefer dependency injection patterns already present in `app/core` when creating new services.
- Extend sample config (`config/environments.yml`, `backend/.env.example`) rather than hardcoding secrets or inline API keys.

## Testing Guidelines
- Uphold the 80% coverage floor noted in `README.md`; mirror frontend specs under `frontend/__tests__/` and backend suites under their feature folder (e.g., `app/features/auth/tests/`).
- Mark long-running suites with `@pytest.mark.integration` or `@pytest.mark.slow` so CI can gate them; default PR checks should stay under 10 minutes.
- Capture AI workflow changes with fixtures in `backend/ai_agents/tests/` and update prompt snapshots when configs evolve.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `docs:`, etc.); keep summaries under 75 characters and in the imperative mood.
- PRs should describe the problem, solution, test evidence, and any migrations; link tickets and include screenshots or API samples when behavior shifts.
- Run lint + tests for both services before requesting review and call out any intentionally skipped checks.

## Agent-Specific Notes
- Industry prompt packs live in `backend/ai_agents/config/`; version new prompt files and log schema updates in `knowledge/`.
- Use feature toggles in `config/environments.yml` to stage new agent behaviors and coordinate Terraform changes with the infra team.
