# Pre-Deploy Config & CI Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Dockerfile to include real migration/seed files, create a manual-dispatch seed workflow, and ensure deploy only runs after CI passes.

**Architecture:** Three-file change — fix Dockerfile COPY commands, create seed.yml manual dispatch workflow, update deploy.yml to use workflow_run trigger so it only deploys on CI success.

**Tech Stack:** Docker multi-stage builds, GitHub Actions workflow_run, uv, alembic, Railway CLI

---

### Task 1: Fix Dockerfile — copy real alembic & seed directories

**Files:**
- Modify: `Dockerfile`

**Problem:** The Dockerfile creates empty stub `alembic/` and `seed/` directories via `mkdir -p`. The actual migration files (`alembic/versions/*.py`, `alembic/env.py`, etc.) and seed scripts are never copied. This causes the Railway `preDeployCommand = "alembic upgrade head"` to fail with "no migration scripts found."

Also, `alembic.ini` is never copied — alembic can't find its config.

**Fix:**
Replace the stub mkdir with real COPY commands; add alembic.ini to both stages.

### Task 2: Create `.github/workflows/seed.yml`

**Files:**
- Create: `.github/workflows/seed.yml`

Manual-dispatch workflow to seed the production Neon database.
Uses `DATABASE_URL` and `JWT_SECRET_KEY` from GitHub repo secrets.
Runs `uv run python -m seed` (no dev deps needed).

### Task 3: Update `.github/workflows/deploy.yml` — depend on CI

**Files:**
- Modify: `.github/workflows/deploy.yml`

Change trigger from `push: branches: [main]` to `workflow_run: workflows: ["CI"]` so deployment only happens after CI passes.
Add condition `if: ${{ github.event.workflow_run.conclusion == 'success' }}`.
