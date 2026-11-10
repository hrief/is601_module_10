# Module 10 implementation reflection

## Design and challenges addressed

The starter defined separate SQLAlchemy bases in the model and database modules.
Unifying the model under the database base makes table creation and test cleanup
operate on the same metadata. The persisted credential is now named `password_hash`.
Raw passwords go through Argon2id hashing with random salts, and response schemas
exclude both the raw password and its hash.

Registration validates data before insertion, while unique constraints protect the
database even if requests race. Integrity failures roll back the transaction and
produce a duplicate-account response. Tests exercise both API-level conflict handling
and direct database writes to verify that uniqueness is enforced below the API.

The previous test fixture used the application database and dropped tables. The new
fixture uses a separate test URL and restricts PostgreSQL database names to `_test`.
This supports quick SQLite checks and the real PostgreSQL service used by Actions.

The original Docker health check required curl even though curl was not installed.
The new image uses Python's standard library, initializes tables on startup, and
runs as an unprivileged user. The pipeline passes the tested image between jobs,
so publication uses the same image that was scanned and smoke-tested.

## Local verification

On November 10, 2026, the full suite passed against a real PostgreSQL 17 container:
90 tests passed with 96% coverage of `app`. The existing browser tests initially
read the result before the asynchronous fetch finished. Using Playwright's retrying
`expect(...).to_have_text(...)` assertions fixed that race. The built Docker image
also returned a healthy response and successfully registered a user without exposing
the password or hash. Image scanning found patchable base-image dependencies, leading
to package upgrades during the image build and removal of pip and its bootstrap
bundle after installation. The final Trivy scan passed with zero fixable HIGH or
CRITICAL findings, and the final image passed health and registration checks.
Remote Actions and Docker Hub evidence
still require a push and account configuration.

## Personal reflection ? complete after running and publishing

This section is intentionally unfinished; add your own experiences rather than
claiming deployment results that have not happened.

- What I learned about SQLAlchemy constraints and transaction rollback:
- What I learned about Pydantic validation versus database enforcement:
- The most difficult setup or deployment issue I personally encountered:
- How I diagnosed and resolved it:
- Actual local test command and result:
- Successful GitHub Actions run URL:
- Docker Hub repository and image tag:
- What I would improve for the final project (for example, migrations and token management):
