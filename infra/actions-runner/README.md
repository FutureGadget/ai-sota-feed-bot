# Docker self-hosted Actions runner

This repository-scoped Linux ARM64 runner keeps the scheduled publishing jobs
off GitHub-hosted compute. It is intended for an Apple-silicon Mac running
Docker Desktop.

The container runs as an unprivileged user, drops Linux capabilities, enables
`no-new-privileges`, and does not mount the host Docker socket or any host
directory. GitHub Actions workflow code still executes inside the container
and receives the workflow's repository secrets, so do not attach this runner
to a public or unrelated repository.

## First-time registration

Docker Desktop must be running. From this directory:

```bash
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

The runner registration and work directory live in the `runner-data` named
volume. Normal container recreation and `docker compose down` preserve them.

## Operation

```bash
docker compose ps
docker compose logs --tail 100 runner
docker compose restart runner
docker compose down
docker compose up --detach
```

Enable **Start Docker Desktop when you sign in** in Docker Desktop settings.
The `restart: unless-stopped` policy brings the runner back when Docker starts.
If the Mac sleeps or Docker is stopped, GitHub queues jobs until the runner is
online again.

## Updating

GitHub's runner normally updates itself in the persistent volume. To replace
the base image deliberately, update the pinned official image tag and digest,
then update the local image tag and rebuild. Font updates must also pin the
Google Fonts commit and both file checksums.

## Removal

First remove the runner in GitHub under **Settings → Actions → Runners**. Then
stop the container with `docker compose down`. Removing the `runner-data`
volume is intentionally a separate manual action because it permanently
deletes the local runner registration and cached workspace.
