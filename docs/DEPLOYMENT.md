# Cloud Run + Neon deployment

These are prepared commands, not actions already performed. Execute them only after explicitly deciding to create/use cloud resources and publish this synthetic demo. No cloud account, project, billing configuration or Neon credential is needed to complete the local build.

## 1. Choose project, region and database

Use an existing billing-enabled Google Cloud project. Install/sign in to `gcloud` and confirm the intended account/project. Choose a Cloud Run region close to the Neon region. Example variables below use Montréal; replace them as appropriate. Commands are Bash-compatible.

```bash
export PROJECT_ID='replace-with-project-id'
export REGION='northamerica-northeast1'
export REPOSITORY='team-directory'
export IMAGE_TAG='v1'
export IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/app:$IMAGE_TAG"
export RUNTIME_SA="team-directory-runtime@$PROJECT_ID.iam.gserviceaccount.com"
export JOB_SA="team-directory-jobs@$PROJECT_ID.iam.gserviceaccount.com"
gcloud config set project "$PROJECT_ID"
```

In Neon, create a project/database for **synthetic data only**. Keep two connection strings:

- **Pooled connection**, with `-pooler` in the hostname: app runtime.
- **Direct connection**, without `-pooler`: Alembic and seed jobs.

Use the SQLAlchemy driver prefix `postgresql+psycopg://` instead of `postgresql://`. Preserve the Neon connection security options, at least `sslmode=require&channel_binding=require`; do not disable TLS. Percent-encode special characters in the username/password. Example only:

```text
postgresql+psycopg://USER:PASSWORD@ep-example-pooler.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require
postgresql+psycopg://USER:PASSWORD@ep-example.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Neon's pooler uses transaction pooling. This application uses short transactions and no session-scoped SQL state. For stricter database privileges, use a separate owner credential for migrations and a runtime role with only the required SELECT/INSERT/UPDATE/DELETE and sequence privileges; remove UPDATE/DELETE on audit tables from that runtime role. The minimal demo setup below can use one database owner credential, whose audit-tampering limitation is documented in the README. [Neon pooling documentation](https://neon.com/docs/connect/connection-pooling), [Neon connection security guidance](https://neon.com/docs/connect/connection-errors).

## 2. Enable services and prepare identities

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com secretmanager.googleapis.com iam.googleapis.com

gcloud artifacts repositories create "$REPOSITORY" \
  --repository-format=docker --location="$REGION" \
  --description='Team Directory container images'

gcloud iam service-accounts create team-directory-runtime \
  --display-name='Team Directory runtime'
gcloud iam service-accounts create team-directory-jobs \
  --display-name='Team Directory migration and seed jobs'
```

These are first-time creation commands; skip existing resources. Your deploying identity needs permissions to build/push images, deploy Cloud Run, manage the selected secrets, and act as these service accounts. Cloud Build's default service account varies by project policy; use `gcloud builds get-default-service-account` to identify it, then grant it Artifact Registry Writer on this repository if missing. Do not grant broad Owner privileges as a shortcut. Organization policy may also restrict public Cloud Run services.

## 3. Store secrets without committing them

Create a local, ignored `.local/production-secrets` directory with restrictive permissions. Put each value into its own file, without a trailing newline; use an editor/password manager to populate connection strings so credentials do not enter shell history.

```bash
mkdir -p .local/production-secrets
chmod 700 .local .local/production-secrets
python3 - <<'PY'
import secrets
from pathlib import Path
root = Path('.local/production-secrets')
for name in ['jwt-secret', 'viewer-password', 'hr-password']:
    path = root / name
    with path.open('x') as file:
        path.chmod(0o600)
        file.write(secrets.token_urlsafe(48 if name == 'jwt-secret' else 24))
PY
# Add the two Neon URL files with your editor:
# .local/production-secrets/database-url
# .local/production-secrets/direct-database-url
chmod 600 .local/production-secrets/*

for name in database-url direct-database-url jwt-secret viewer-password hr-password; do
  gcloud secrets create "team-directory-$name" --replication-policy=automatic
  gcloud secrets versions add "team-directory-$name" \
    --data-file=".local/production-secrets/$name"
done

for name in database-url jwt-secret; do
  gcloud secrets add-iam-policy-binding "team-directory-$name" \
    --member="serviceAccount:$RUNTIME_SA" --role=roles/secretmanager.secretAccessor
done
for name in direct-database-url jwt-secret viewer-password hr-password; do
  gcloud secrets add-iam-policy-binding "team-directory-$name" \
    --member="serviceAccount:$JOB_SA" --role=roles/secretmanager.secretAccessor
done
```

The service does not need demo password environment variables: only the seed job hashes and stores them. Share demo login passwords intentionally with reviewers; never expose the JWT secret or DB credentials. Pin secret **version numbers** in deployments. The following examples assume the first version is `1`. On rotation, add a new version and update the referencing jobs/service; JWT-secret rotation invalidates old access tokens. Changing a demo-password secret does not change an existing user's password because seeding preserves accounts.

## 4. Build the Linux container

From the repository root:

```bash
gcloud builds submit --config=deploy/cloudbuild.yaml --substitutions="_IMAGE=$IMAGE" .
```

Cloud Build uses the root multi-stage Dockerfile: React build, locked Python dependency build, then a non-root Python runtime containing both. `.gcloudignore` and `.dockerignore` exclude local secrets, dependency directories and unrelated artifacts. The build file explicitly targets Linux AMD64 for Cloud Run, independently of an Apple Silicon laptop. A new release should use a new immutable tag (or deploy its digest).

## 5. Migrate, then seed, as separate jobs

```bash
gcloud run jobs deploy team-directory-migrate \
  --region="$REGION" --image="$IMAGE" --service-account="$JOB_SA" \
  --tasks=1 --parallelism=1 --max-retries=0 --task-timeout=300s \
  --cpu=1 --memory=512Mi \
  --set-secrets='DATABASE_URL=team-directory-direct-database-url:1,JWT_SECRET=team-directory-jwt-secret:1' \
  --command=alembic --args=upgrade,head
gcloud run jobs execute team-directory-migrate --region="$REGION" --wait

gcloud run jobs deploy team-directory-seed \
  --region="$REGION" --image="$IMAGE" --service-account="$JOB_SA" \
  --tasks=1 --parallelism=1 --max-retries=0 --task-timeout=300s \
  --cpu=1 --memory=512Mi \
  --set-secrets='DATABASE_URL=team-directory-direct-database-url:1,JWT_SECRET=team-directory-jwt-secret:1,DEMO_VIEWER_PASSWORD=team-directory-viewer-password:1,DEMO_HR_PASSWORD=team-directory-hr-password:1' \
  --command=python --args=-m,app.seed
gcloud run jobs execute team-directory-seed --region="$REGION" --wait
```

Stop if either job fails. Review its execution logs (never print environment variables). Do not run migrations concurrently. The jobs get the **direct** URL as `DATABASE_URL`; Alembic also supports `DIRECT_DATABASE_URL` as an override for local/operator use. JWT configuration is required by the shared settings module even though a migration does not issue tokens.

On later deployments, rerun migration with the new image, skip seed unless needed, then roll out the app. Prefer additive/backward-compatible schema changes: an old revision may serve traffic while the new revision starts. Back up before destructive changes; rolling a service back does not roll its database schema back. [Cloud Run job flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/jobs/deploy).

**Role migration exception (`b719d2e4a630`):** this revision replaces `users.role` with `roles` and `user_roles`, and the updated API replaces the singular `role` field with a `roles` array. It is incompatible with the old application. For an existing deployment, use a maintenance window to stop application traffic before the migration job, apply it with the new image, deploy the matching backend/frontend, and restore traffic only after verification. Do not leave old revisions serving against the new schema. Existing users and assignments are preserved. Downgrading requires exactly one built-in role per user and no custom roles; the migration rejects other states to prevent silent data loss. See the README's migration section for local upgrade commands.

## 6. Deploy one service

```bash
gcloud run deploy team-directory \
  --region="$REGION" --image="$IMAGE" --service-account="$RUNTIME_SA" \
  --allow-unauthenticated --port=8080 \
  --cpu=1 --memory=512Mi --concurrency=8 --timeout=60s \
  --cpu-throttling --min=0 --max=2 \
  --set-env-vars='DB_POOL_SIZE=2,ACCESS_TOKEN_MINUTES=30' \
  --set-secrets='DATABASE_URL=team-directory-database-url:1,JWT_SECRET=team-directory-jwt-secret:1' \
  --startup-probe='httpGet.path=/health,httpGet.port=8080,initialDelaySeconds=0,timeoutSeconds=1,periodSeconds=3,failureThreshold=20'

SERVICE_URL=$(gcloud run services describe team-directory --region="$REGION" \
  --format='value(status.url)')
curl --fail "$SERVICE_URL/health"
```

`--allow-unauthenticated` makes the login page and documentation reachable; application endpoints still require JWT authentication and permissions. If organization policy disallows public invocation, resolve that policy deliberately with your administrator rather than weakening access controls elsewhere. Cloud Run supplies `PORT`; the container runs one Uvicorn process bound to `0.0.0.0`. The health check reports process liveness, not database readiness. No background tasks or in-instance migrations are required.

The initial setting uses **request-based billing** (`--cpu-throttling`), **minimum 0** and **service-level maximum 2**. Each process allows a pool of two DB connections with `max_overflow=0`, so steady state at two instances is at most four app-side connections; deployments, retries and jobs can add transient connections, and platform maximums are not an absolute instantaneous cap. Monitor actual Neon use. Keep a single application worker unless recalculating the total pool budget. [Cloud Run deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy), [billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings).

After deployment, run the README demonstration against the URL and check `/docs`, `/openapi.json`, a direct `/people/1` link, JSON 404s at `/api/unknown`, Viewer restrictions, HR reveal and audit history. Do not point destructive integration/browser tests at the production database.

## Startup latency and cost

Minimum 0 permits scale-to-zero and can introduce cold-start latency. Neon may also suspend compute, adding another startup delay. To keep one Cloud Run instance warm while retaining request-based billing:

```bash
gcloud run services update team-directory --region="$REGION" --min=1 --cpu-throttling
# Return to scale-to-zero:
gcloud run services update team-directory --region="$REGION" --min=0 --cpu-throttling
```

Minimum 1 usually improves application startup latency but incurs idle-instance charges and does not guarantee Neon stays awake. Costs depend on traffic, region, runtime, build/storage usage, logs, networking and the chosen Neon plan; no fixed or zero bill is promised. Set budget alerts and check current pricing before deploying. Changing these settings can itself affect cost. [Cloud Run minimum instances](https://docs.cloud.google.com/run/docs/configuring/min-instances).

## Operations and cleanup

- Use Google Secret Manager for runtime credentials and HTTPS/TLS for both browser and database connections.
- Keep database/HTTP debug logging off. Application error responses and handlers omit sensitive inputs and SQL error text; do not add request-body or token logging during troubleshooting.
- Retain backups, manage Neon restore capability, and choose audit retention before using anything beyond synthetic data.
- To retire the demo, deliberately delete the Cloud Run service and its jobs, then review image, secret and Neon resources separately. Stopping a service does not delete or stop every chargeable resource.
- No resource creation, build submission, deployment, Git push, or billing change was performed as part of implementation.
