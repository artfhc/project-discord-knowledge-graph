#!/bin/bash
# Google Cloud VM Setup Script for Discord Knowledge Graph Pipeline
set -e

echo "🚀 Setting up Discord Knowledge Graph VM on Google Cloud..."

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install essential packages
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    unzip \
    git \
    python3 \
    python3-pip

# Install Docker
echo "📦 Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Install Google Cloud CLI
echo "☁️ Installing Google Cloud CLI..."
curl https://sdk.cloud.google.com | bash
source ~/.bashrc

# Create project directories
mkdir -p ~/discord-kg/{exports,scripts,config,logs}

# Set up environment
echo "⚙️ Setting up environment..."
cat > ~/discord-kg/config/.env << 'EOF'
# Discord Configuration
DISCORD_TOKEN=your_discord_token_here

# Google Cloud Configuration  
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_BUCKET=your_storage_bucket

# Export Configuration
EXPORT_FORMAT=json
EXPORT_PATH=/home/$USER/discord-kg/exports
LOG_PATH=/home/$USER/discord-kg/logs

# Schedule Configuration (cron format)
EXPORT_SCHEDULE="0 2 * * *"  # Daily at 2 AM
EOF

echo "✅ VM setup complete!"
echo ""
echo "Next steps:"
echo "1. Log out and back in to apply Docker group membership"
echo "2. Configure your Discord token in ~/discord-kg/config/.env"
echo "3. Set up Google Cloud authentication: gcloud auth login"
echo "4. Run the Discord exporter setup script"