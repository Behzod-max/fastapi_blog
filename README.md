# FastAPI Blog

FastAPI blog API with PostgreSQL/SQLite support, JWT authentication, Alembic
migrations, configurable CORS, rate limiting, and production deployment files.

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set a unique `SECRET_KEY` and the correct
   `DATABASE_URL`. Set `ALLOWED_ORIGINS` to a comma-separated list of frontend
   origins, with no trailing slash.
4. Start the development server:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

The interactive API docs are at `/docs` and `/redoc` in development. Existing
routes remain available (for example, `/posts/` and `/login`); versioned aliases
are also available under `/api/v1` (for example, `/api/v1/posts/`).

`GET /health` runs `SELECT 1` against the configured database and returns HTTP
503 if the database probe fails. The posts list endpoint is limited to 10
requests per minute per client IP. Its default in-memory rate-limit storage is
per worker; use shared storage such as Redis if limits must be consistent across
multiple production workers or instances.

## Production deployment

The production server files target Linux. Install the production dependencies,
apply migrations, and start Gunicorn with:

```bash
python -m pip install -r requirements-production.txt
python -m alembic upgrade head
bash start.sh
```

`PORT` and `WEB_CONCURRENCY` can be set in the environment. Production should
set `ENVIRONMENT=production`, `DEBUG=false`, a strong `SECRET_KEY`, the
production database URL, and the exact frontend origins in `ALLOWED_ORIGINS`.
Interactive API docs are disabled when `ENVIRONMENT=production`. `start.sh`
uses the project's `.venv` by default; set `VENV_DIR` if your virtual
environment uses another directory.

For a new EC2/systemd setup, adjust the paths and service user in
[`deploy/fast_api_blog.service`](./deploy/fast_api_blog.service), copy it to
`/etc/systemd/system/fast_api_blog.service`, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fast_api_blog
```

The existing GitHub Actions workflow runs tests and then deploys automatically
when code is pushed to `master`. Configure these repository Actions secrets:
`EC2_HOST`, `EC2_SSH_KEY` (private key contents), `EC2_KNOWN_HOSTS` (the
trusted server host-key line), `EC2_USER`, `EC2_APP_DIR`, and
`EC2_SERVICE_NAME`. Set `EC2_APP_DIR` to the checked-out project directory
(for example, `/var/www/fast_api_blog`) and make the systemd unit's
`WorkingDirectory`, `EnvironmentFile`, and `ExecStart` paths match it.

After CI succeeds, the workflow runs `deploy.sh` on the server as `ubuntu` in
`/var/www/fastapi_blog`, then verifies that `fastapi_blog.service` is active and
that its health endpoint responds on port 8001. The script pulls `master`,
creates `venv` if needed, installs production dependencies, applies existing
Alembic migrations with `alembic upgrade head`, and restarts the systemd
service. A migration failure stops the deployment before the service is
restarted. The EC2 deploy user needs Git access to the repository and
non-interactive `sudo` permission for restarting that service.

Configure these repository Actions secrets: `EC2_HOST`, `EC2_SSH_KEY` (private
key contents), and `EC2_KNOWN_HOSTS` (the verified SSH host-key line). To
obtain the host key securely, read the EC2 instance's SSH host public key
fingerprint through a trusted channel such as the EC2 console/SSM, verify it,
then add its `known_hosts` line as the secret. Do not rely on an unverified
`ssh-keyscan` result as the trust source.

For manual deploys, run `bash deploy.sh` from the project directory; override
`DEPLOY_BRANCH`, `SERVICE_NAME`, or `VENV_DIR` if needed.

Cloud resources, DNS, TLS, firewall rules, and provider-specific secrets still
need to be configured in the hosting provider; this repository does not deploy
to AWS, Render, or Railway automatically.
