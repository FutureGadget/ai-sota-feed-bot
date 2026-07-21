# Docker self-hosted Actions runner

This repository-scoped Linux ARM64 runner keeps the scheduled publishing jobs
off GitHub-hosted compute. It is intended for an Apple-silicon Mac running
Docker Desktop.

The container runs as an unprivileged user, drops Linux capabilities, enables
`no-new-privileges`, and does not mount the host Docker socket. Its only host
mount is a dedicated, otherwise-empty job workspace. GitHub Actions workflow
code still executes inside the container and receives the workflow's repository
secrets, so do not attach this runner to a public or unrelated repository.

## First-time registration

Docker Desktop must be running. From this directory:

```bash
mkdir -p "$HOME/.local/share/llm-digest-actions-runner/work"
cp .env.example .env
# Edit .env so RUNNER_WORK_DIR is the absolute path created above.
docker compose build --pull
RUNNER_TOKEN="$(gh api --method POST \
  repos/FutureGadget/ai-sota-feed-bot/actions/runners/registration-token \
  --jq .token)" docker compose up --detach
docker compose logs --follow runner
```

Wait for `Listening for Jobs`, then press Ctrl-C to stop following the logs.
Recreate the container once without the one-hour registration token so it no
longer appears in the container configuration:

```bash
docker compose up --detach --force-recreate
```

Runner credentials live in the small `runner-state` named volume. The checked
out repositories and tool cache live in `RUNNER_WORK_DIR` on the Mac so they do
not consume Docker Desktop's virtual disk. Normal container recreation and
`docker compose down` preserve both.

## Operation

```bash
docker compose ps
docker compose logs --tail 100 runner
docker compose restart runner
docker compose down
docker compose up --detach
```

Docker retains at most three 10 MB log files for the container. GitHub's runner
prints detailed diagnostics to standard output, including benign canceled-poll
stack traces when a completed job changes the runner from busy to online, so
bounded rotation prevents those diagnostics from growing without limit.

Enable **Start Docker Desktop when you sign in** in Docker Desktop settings.
The `restart: unless-stopped` policy brings the runner back when Docker starts.
If the Mac sleeps or Docker is stopped, GitHub queues jobs until the runner is
online again.

## Updating

GitHub can update the running container's runner binary, but container
recreation returns to the version baked into the image. To update durably,
change the pinned official image tag and digest, update the local image tag,
and rebuild. Font updates must also pin the Google Fonts commit and both file
checksums.

## Removal

First remove the runner in GitHub under **Settings → Actions → Runners**. Then
stop the container with `docker compose down`. Removing the `runner-state`
volume and `RUNNER_WORK_DIR` are intentionally separate manual actions because
they permanently delete the local runner registration and cached workspace.
