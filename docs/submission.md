# Submission checklist

- Repository: https://github.com/hrief/is601_module_10
- Confirm this repository is accessible to the grader and contains your reviewed changes.
- The local origin initially pointed to the instructor repository. Before pushing,
  use `git remote set-url origin https://github.com/hrief/is601_module_10.git`.
- Create a Docker Hub repository and replace the README placeholder with its real link.
- Configure `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, and `DOCKERHUB_REPOSITORY` as documented.
- Push to main and resolve any failures; do not disable the scan to obtain a green run.
- Capture a screenshot of the successful Actions run with test, image, and deploy jobs visible.
  Save it as `docs/screenshots/github-actions-success.png`.
- Capture the Docker Hub repository tags page showing `latest` and the commit tag.
  Save it as `docs/screenshots/docker-hub-tags.png`.
- Pull and run the published image, then verify `/health` and user registration.
- Add your own experiences to `reflection.md`; include actual run and Docker Hub links.

Screenshots and successful remote runs are pending. They must be captured from real
results after publication, not generated or substituted with local output.
