from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    "ci.yml",
    "feed-full-publish.yml",
    "email-digest.yml",
    "feedback-sync.yml",
    "feed-ops-summary.yml",
    "i18n-translate.yml",
    "models-refresh.yml",
)


class HostedRunnerConfigTest(unittest.TestCase):
    def test_workflows_use_github_hosted_standard_runners(self):
        for filename in WORKFLOWS:
            with self.subTest(workflow=filename):
                workflow = (ROOT / ".github" / "workflows" / filename).read_text()
                self.assertIn("runs-on: ubuntu-latest", workflow)
                self.assertNotIn("self-hosted", workflow)

    def test_full_publish_preserves_dry_run_and_hosted_prerequisites(self):
        workflow = (
            ROOT / ".github" / "workflows" / "feed-full-publish.yml"
        ).read_text()
        self.assertIn("dry_run:", workflow)
        self.assertIn("ubuntu-latest", workflow)
        self.assertNotIn("runner:", workflow)
        self.assertIn("actions/setup-node@v4", workflow)
        self.assertIn('node-version: "24"', workflow)
        self.assertIn(
            'git config --global --replace-all safe.directory "$GITHUB_WORKSPACE"',
            workflow,
        )
        self.assertNotIn("inputs.runner", workflow)
        self.assertIn("sudo apt-get install -y fonts-nanum", workflow)
        self.assertIn("github.ref != 'refs/heads/main'", workflow)
        self.assertIn("Publishing is only allowed from main", workflow)
        self.assertIn(
            "AUTO_PUSH_RUNTIME: ${{ inputs.dry_run && '0' || '1' }}", workflow
        )

    def test_full_publish_fails_when_runtime_git_operations_fail(self):
        script = (
            ROOT
            / "skills"
            / "ai-feed-digest-local"
            / "scripts"
            / "run_full.sh"
        ).read_text()
        self.assertNotIn("git add data/ web/ || true", script)
        self.assertNotIn(
            'git commit -m "chore(data): refresh feed artifacts '
            '$(date +%F\\ %H:%M)" || true',
            script,
        )
        self.assertIn("git rev-parse --is-inside-work-tree", script)
        self.assertIn("git push origin HEAD:main", script)
        self.assertIn("runtime_push_failed=true", script)
        failure_marker = script.index("runtime_push_failed=true")
        self.assertIn("exit 1", script[failure_marker:])

    def test_runner_image_pins_and_verifies_the_official_release(self):
        dockerfile = (ROOT / "infra" / "actions-runner" / "Dockerfile").read_text()
        self.assertIn(
            "FROM ghcr.io/actions/actions-runner:2.336.0@sha256:0cfdcc701ce933c6d243c6b0b2da767366dc9f2e99961d4c3754b0b78084cdda",
            dockerfile,
        )
        self.assertIn("sha256sum --check", dockerfile)
        self.assertIn(
            "16680f8688ffcd467d2eb2146a9ce0343404581d",
            dockerfile,
        )
        self.assertIn(
            "76f45ef4a6bcff344c837c95a7dcc26e017e38b5846d5ae0cdcb5b86be2e2d31",
            dockerfile,
        )
        self.assertIn(
            "21f9d3a7f1ca82ca1dc9a288e30138b4f1feb6e71fc89b5a9181fed174b6bbe2",
            dockerfile,
        )
        self.assertIn("USER runner", dockerfile)

    def test_compose_does_not_expose_the_host_docker_daemon(self):
        compose = (ROOT / "infra" / "actions-runner" / "compose.yaml").read_text()
        self.assertNotIn("docker.sock", compose)
        self.assertNotIn("privileged:", compose)
        self.assertIn("no-new-privileges:true", compose)
        self.assertIn("cap_drop:", compose)
        self.assertIn("- ALL", compose)
        self.assertIn("restart: unless-stopped", compose)
        self.assertIn("source: ${RUNNER_WORK_DIR:?", compose)
        self.assertIn("target: /home/runner/_work", compose)
        self.assertIn("target: /runner-state", compose)

    def test_compose_bounds_runner_log_storage(self):
        compose = (ROOT / "infra" / "actions-runner" / "compose.yaml").read_text()
        self.assertIn("driver: json-file", compose)
        self.assertIn('max-size: "10m"', compose)
        self.assertIn('max-file: "3"', compose)

    def test_registration_token_is_only_required_for_first_registration(self):
        entrypoint = (
            ROOT / "infra" / "actions-runner" / "entrypoint.sh"
        ).read_text()
        self.assertIn('if [ ! -f "$RUNNER_HOME/.runner" ]; then', entrypoint)
        self.assertIn('require_env "RUNNER_TOKEN"', entrypoint)
        self.assertIn("unset RUNNER_TOKEN", entrypoint)
        self.assertIn("RUNNER_STATE=/runner-state", entrypoint)
        self.assertIn('ln --symbolic --force "$RUNNER_STATE/$filename"', entrypoint)


if __name__ == "__main__":
    unittest.main()
