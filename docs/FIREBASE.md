# Production deployment

Team Directory uses three services:

- Firebase Hosting site `team-directory` in GCP project `nuvorima` serves the frontend. This project remains without billing.
- Cloud Run service `team-directory` in project `invoiceparse-java`, region `northamerica-northeast2`, runs FastAPI.
- The free Neon project `team-directory`, managed through Vercel, stores PostgreSQL data.

The browser calls Cloud Run directly using the public build-time `VITE_API_BASE_URL`.
The backend allows the two Firebase production origins through CORS. Bearer tokens
remain in browser memory; database credentials and the JWT secret stay in Secret
Manager. `scripts/prepare-hosting.mjs` validates the HTTPS API origin and generates
an ignored, single-site `firebase.json` with matching CSP. Firebase does not proxy
API calls and needs no billing account for this arrangement.

## Release flow

Pull requests run checks only. After a merge/push to `main`, `deploy-production`
waits for `verify`, rejects superseded production commits, authenticates with
GitHub OIDC, builds/pushes the backend image tagged with the commit SHA, executes
the migration job, updates Cloud Run, checks health and deploys Firebase Hosting.
Production releases are serialized. No preview environment or channel is used.

The first deployment provisions and seeds the database separately. Routine releases
run migrations but do not reseed. Schema changes must remain compatible with the
previous serving revision. The existing role migration is incompatible with older
versions; see [DEPLOYMENT.md](DEPLOYMENT.md) before upgrading any older installation.
A failed Hosting deployment after a successful backend update leaves the previous
frontend live; keep API changes backward-compatible. Rollback does not undo schema
migrations.

## GitHub production environment variables

| Variable | Value |
| --- | --- |
| `FIREBASE_PROJECT_ID` | `nuvorima` |
| `FIREBASE_HOSTING_SITE_ID` | `team-directory` |
| `FIREBASE_CLI_VERSION` | `15.29.0` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/229075086851/locations/global/workloadIdentityPools/nuvorima-github/providers/github` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `team-directory-prod-deployer@nuvorima.iam.gserviceaccount.com` |
| `GCP_BACKEND_PROJECT_ID` | `invoiceparse-java` |
| `CLOUD_RUN_REGION` | `northamerica-northeast2` |
| `VITE_API_BASE_URL` | The verified Cloud Run service origin |

The production identity trusts repository ID `1357719967`, push events on `main`,
and `.github/workflows/ci.yml` through the shared provider. Its Hosting roles apply
to project `nuvorima`; the generated one-site manifest limits deployment behavior,
not the project's IAM boundary. Backend permissions are limited to Team Directory's
image repository, service, migration job, and runtime/job identities. The deployer
has no direct Secret Manager accessor role.

## Runtime settings and verification

Cloud Run uses one CPU, 512 MiB, request-based billing, minimum zero and maximum
two instances, with a two-connection application pool. Scale-to-zero can introduce
cold-start latency. The database's free plan has its own resource limits; GCP image
storage, builds, runtime and networking may incur charges in `invoiceparse-java`.

`deploy/production.env.yaml` holds non-secret runtime settings. Secret version 1
is pinned in the initial service and job definitions; rotate secrets deliberately
and update those version references. Seed account passwords are private owner
configuration and are not embedded in the frontend.

Backend tests use a dedicated local PostgreSQL database. Browser tests explicitly
use different frontend and API origins to cover real CORS behavior. Before calling
a release healthy, verify Firebase assets and direct profile links, successful
login/directory reads, Viewer restrictions, HR reveal/audit and logout. Do not run
destructive integration tests against the production database.
