#!/bin/bash
# Google Cloud Storage setup script
set -e

PROJECT_ID="your-gcp-project-id"
BUCKET_NAME="discord-kg-exports"
SERVICE_ACCOUNT_NAME="discord-kg-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🌩️ Setting up Google Cloud Storage for Discord KG..."

# Create storage bucket
echo "📦 Creating storage bucket: $BUCKET_NAME"
gsutil mb -p $PROJECT_ID gs://$BUCKET_NAME

# Set bucket lifecycle (optional - auto-delete old exports after 90 days)
cat > /tmp/lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": {
        "type": "Delete"
      },
      "condition": {
        "age": 90
      }
    }
  ]
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME
rm /tmp/lifecycle.json

# Create service account
echo "👤 Creating service account: $SERVICE_ACCOUNT_NAME"
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Discord Knowledge Graph Service Account" \
    --description="Service account for Discord KG pipeline"

# Grant storage permissions
echo "🔑 Granting storage permissions..."
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT_EMAIL:objectAdmin gs://$BUCKET_NAME

# Create and download service account key
echo "🔐 Creating service account key..."
gcloud iam service-accounts keys create ~/discord-kg/config/gcp-service-account.json \
    --iam-account=$SERVICE_ACCOUNT_EMAIL

echo "✅ Google Cloud Storage setup complete!"
echo ""
echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Bucket Name: $BUCKET_NAME"
echo "  Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "  Key File: ~/discord-kg/config/gcp-service-account.json"
echo ""
echo "Update your .env file with:"
echo "  GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "  GOOGLE_CLOUD_BUCKET=$BUCKET_NAME"