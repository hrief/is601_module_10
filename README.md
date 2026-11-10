# Secure User Calculator ? Module 10

Repository: [hrief/is601_module_10](https://github.com/hrief/is601_module_10)

A FastAPI calculator extended with PostgreSQL-backed user registration, Argon2id
password hashing, validated Pydantic input/output schemas, and JWT authentication.
The `users` table enforces unique usernames and emails, stores `password_hash`,
and records creation/update timestamps. `UserRead` excludes password fields.
Existing calculator routes and the browser interface remain available.

## Run locally

Use Python 3.13 and Docker Desktop with Linux containers.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value in `.env` as `SECRET_KEY`, then run:

```powershell
docker compose up --build -d
```

Visit http://localhost:8000 and http://localhost:8000/docs. The container initializes
new database tables before starting Uvicorn. For a host-based server instead:

```powershell
docker compose up -d db
python -m app.database_init
python -m uvicorn main:app --reload
```

`POST /users` accepts `username`, `email`, and `password`; first/last names are
optional. Passwords require 6?128 characters with uppercase, lowercase, and a digit.
`POST /token` accepts JSON `username` (or email) and `password`, returning a bearer
token. Use it in `Authorization: Bearer <token>` for `GET /users/me`.
Invalid input returns 400, duplicate registration 409, and invalid credentials 401.
The signing key must stay private and be shared across application processes.

## Run tests

Fast local checks use an isolated in-memory SQLite database:

```powershell
python -m pytest tests/unit tests/integration --run-slow
```

For the assignment's real PostgreSQL tests:

```powershell
docker compose --profile test up -d --wait test-db
$env:TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/fastapi_test"
python -m playwright install chromium
python -m pytest --run-slow --junitxml=test-results/junit.xml
```

On macOS/Linux, activate with `source .venv/bin/activate` and use
`export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/fastapi_test`.
Tests cover salted hashes, wrong passwords, schema validation, secret-free responses,
database uniqueness, rollback after constraint failures, registration, login,
protected profiles, calculator APIs, and browser interactions.
Tests never use `DATABASE_URL` for their database. `TEST_DATABASE_URL` must point to
a disposable database ending in `_test`; fixtures create its tables and delete test
rows. Do not point it at a database containing data you need. SQLite checks are a
convenience; GitHub Actions explicitly runs against PostgreSQL 17.

## GitHub Actions and Docker Hub

[Workflow runs](https://github.com/hrief/is601_module_10/actions)

1. Create a public Docker Hub repository, for example `YOUR_DOCKERHUB_USERNAME/is601-module-10`.
2. In GitHub **Settings ? Secrets and variables ? Actions**, add secrets
   `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (a Docker Hub access token with write access).
3. Add repository variable `DOCKERHUB_REPOSITORY` with `username/repository`.
4. Push your code to `main`. Pull requests run tests, scanning, and smoke tests;
   main pushes also publish the image after those checks pass.

Docker Hub repository: **pending creation**.
Replace this placeholder link after creating it:
[Docker Hub image repository](https://hub.docker.com/r/YOUR_DOCKERHUB_USERNAME/is601-module-10).
No successful deployment is claimed until the repository is configured and the workflow passes.

The pipeline runs all tests against PostgreSQL, uploads test/coverage reports,
builds the runtime image, blocks fixable HIGH/CRITICAL vulnerabilities with Trivy,
and smoke-tests registration against a second PostgreSQL container. It transfers
the tested image as an artifact to the deployment job, which pushes `latest` and
the full commit SHA to Docker Hub. Publishing an image is the deployment for this
assignment; it does not provision a public application host.

After publication, verify the pulled image (replace the image name):

```powershell
docker pull YOUR_DOCKERHUB_USERNAME/is601-module-10:latest
docker compose up -d db
docker run --rm -p 8001:8000 --env-file .env -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/fastapi_db YOUR_DOCKERHUB_USERNAME/is601-module-10:latest
```

Open http://localhost:8001/health and http://localhost:8001/docs.
Application and test dependencies are listed in `requirements.txt`. The image
runs as a non-root user and uses a Python HTTP health check. System packages and
installation tooling are upgraded during the build; pip and its bootstrap bundle
are removed after dependencies are installed.

## Submission

See [submission checklist](docs/submission.md) and [implementation reflection](docs/reflection.md).
This project extends the supplied calculator starter. The module changes include
Argon2id hashing, the hash column, unified metadata, API routes, safe test database
selection, new security/API tests, and a build/scan/smoke-test/publish pipeline.
Review and explain these changes in your own reflection before submitting.

For an existing database made with the starter's `password` column, use a schema
migration before deploying this version: `create_all` only creates missing tables.
Starter bcrypt hashes also require a deliberate password reset or migration; this
version verifies Argon2id hashes. Fresh assignment databases need no migration.

Implementation references: [pwdlib hashing](https://frankie567.github.io/pwdlib/reference/pwdlib/)
and [Docker test-before-push workflow](https://docs.docker.com/build/ci/github-actions/test-before-push/).
