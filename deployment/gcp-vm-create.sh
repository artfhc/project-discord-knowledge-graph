#!/bin/bash
# Google Cloud VM Creation Script
set -e

# Configuration
PROJECT_ID="discord-knowledge-graph"
INSTANCE_NAME="discord-kg-vm"
ZONE="us-central1-a"
MACHINE_TYPE="e2-small"
BOOT_DISK_SIZE="20GB"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

echo "🚀 Creating Google Cloud VM for Discord Knowledge Graph..."

# Validate PROJECT_ID
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo "❌ Error: Please provide your GCP project ID"
    echo "Usage: $0 YOUR_PROJECT_ID"
    echo "Or edit the script to set PROJECT_ID"
    exit 1
fi

echo "📋 Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Instance Name: $INSTANCE_NAME"
echo "  Zone: $ZONE"
echo "  Machine Type: $MACHINE_TYPE"
echo ""

# Create the VM instance
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --network-interface=network-tier=PREMIUM,subnet=default \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=default \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --create-disk=auto-delete=yes,boot=yes,device-name=$INSTANCE_NAME,image=projects/$IMAGE_PROJECT/global/images/family/$IMAGE_FAMILY,mode=rw,size=$BOOT_DISK_SIZE,type=projects/$PROJECT_ID/zones/$ZONE/diskTypes/pd-balanced \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=project=discord-kg,env=production \
    --reservation-affinity=any

echo "✅ VM created successfully!"
echo ""
echo "VM Details:"
echo "  Name: $INSTANCE_NAME"
echo "  Zone: $ZONE"  
echo "  Machine Type: $MACHINE_TYPE"
echo ""
echo "Next steps:"
echo "1. Set up Discord token in Secret Manager:"
echo "   ./deployment/setup-secrets.sh"
echo ""
echo "2. SSH into the VM:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
echo ""
echo "3. Clone the repository and run setup:"
echo "   git clone https://github.com/artfhc/project-discord-knowledge-graph.git"
echo "   cd project-discord-knowledge-graph"
echo "   ./deployment/gcp-setup.sh YOUR_DISCORD_TOKEN"
echo ""
echo "4. The VM will automatically:"
echo "   - Install Docker and Docker Compose"
echo "   - Set up DiscordChatExporter container"
echo "   - Configure automated exports to GCS"
echo "   - Create systemd service for auto-start"
echo ""
echo "5. Monitor logs:"
echo "   sudo journalctl -u discord-kg-pipeline -f"