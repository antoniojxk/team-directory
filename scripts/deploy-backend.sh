#!/usr/bin/env bash
set -euo pipefail
: "${GCP_BACKEND_PROJECT_ID:?Set GCP_BACKEND_PROJECT_ID}"
: "${CLOUD_RUN_REGION:?Set CLOUD_RUN_REGION}"
: "${BACKEND_IMAGE:?Set BACKEND_IMAGE to an immutable image tag or digest}"

# The jobs and runtime identities are provisioned once by the project owner.
# Run migrations serially, before replacing the serving revision.
gcloud run jobs update team-directory-migrate \
  --project="$GCP_BACKEND_PROJECT_ID" --region="$CLOUD_RUN_REGION" \
  --image="$BACKEND_IMAGE" --quiet
gcloud run jobs execute team-directory-migrate \
  --project="$GCP_BACKEND_PROJECT_ID" --region="$CLOUD_RUN_REGION" --wait --quiet
gcloud run services update team-directory \
  --project="$GCP_BACKEND_PROJECT_ID" --region="$CLOUD_RUN_REGION" \
  --image="$BACKEND_IMAGE" --env-vars-file=deploy/production.env.yaml --quiet
url=$(gcloud run services describe team-directory \
  --project="$GCP_BACKEND_PROJECT_ID" --region="$CLOUD_RUN_REGION" --format='value(status.url)')
curl --fail --silent --show-error --retry 3 "$url/health"
