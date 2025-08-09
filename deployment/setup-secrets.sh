#!/bin/bash
# Store Discord token in Google Secret Manager
set -e

PROJECT_ID="discord-knowledge-graph"
SECRET_NAME="discord-token"

echo "🔐 Setting up Discord token in Google Secret Manager..."

# Create the secret
echo "Creating secret..."
gcloud secrets create $SECRET_NAME \
    --project=$PROJECT_ID \
    --replication-policy="automatic"

# Add the token value (you'll be prompted to enter it securely)
echo "Please enter your Discord token:"
read -s DISCORD_TOKEN
echo "$DISCORD_TOKEN" | gcloud secrets versions add $SECRET_NAME \
    --project=$PROJECT_ID \
    --data-file=-

# Grant access to compute service account
COMPUTE_SA=$(gcloud iam service-accounts list \
    --filter="displayName:Compute Engine default service account" \
    --format="value(email)" \
    --project=$PROJECT_ID)

gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

echo "✅ Secret created successfully!"
echo "Secret name: $SECRET_NAME"
echo "Project: $PROJECT_ID"