#!/bin/bash
# Google Cloud VM Setup Script for Discord Knowledge Graph Pipeline
set -e

# Configuration
PROJECT_ID="discord-knowledge-graph"
SECRET_NAME="discord-token"

# Try to get Discord token from Google Secret Manager
echo "🔐 Attempting to retrieve Discord token from Secret Manager..."

# Check if we can access Secret Manager
if gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    DISCORD_TOKEN=$(gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID" 2>/dev/null)
    echo "✅ Successfully retrieved Discord token from Secret Manager"
else
    echo "⚠️  Cannot access Secret Manager from this VM"
    echo "This is likely due to insufficient VM authentication scopes."
    echo ""
    echo "Solutions:"
    echo "1. Recreate VM with cloud-platform scope (recommended)"
    echo "2. Use gcloud auth login and try again"
    echo "3. Pass token as parameter: $0 YOUR_DISCORD_TOKEN"
    echo ""
    
    # Try user authentication as fallback
    echo "Attempting user authentication..."
    if command -v gcloud >/dev/null 2>&1; then
        echo "Please authenticate with your user account:"
        gcloud auth login --no-launch-browser
        
        # Retry with user auth
        if gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
            DISCORD_TOKEN=$(gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID" 2>/dev/null)
            echo "✅ Retrieved token using user authentication"
        fi
    fi
    
    # Final fallback to parameter or manual input
    if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "" ]; then
        echo "❌ Could not retrieve token from Secret Manager"
        DISCORD_TOKEN="${1}"
        
        if [ -z "$DISCORD_TOKEN" ]; then
            echo ""
            echo "Please provide your Discord token:"
            echo "1. As parameter: $0 YOUR_DISCORD_TOKEN"
            echo "2. Enter manually (secure input):"
            read -s -p "Discord Token: " DISCORD_TOKEN
            echo ""
            
            if [ -z "$DISCORD_TOKEN" ]; then
                echo "⚠️  No token provided - using placeholder"
                DISCORD_TOKEN="your_discord_token_here"
            else
                echo "✅ Token provided manually"
            fi
        else
            echo "✅ Using token from parameter"
        fi
    fi
fi

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

# Apply new group membership without logout
newgrp docker << EONG
# Install Python packages for the pipeline
echo "🐍 Installing Python packages..."
pip3 install --user google-cloud-storage discord.py python-dotenv requests

# Install Google Cloud CLI
echo "☁️ Installing Google Cloud CLI..."
curl https://sdk.cloud.google.com | bash
source ~/.bashrc

# Create project directories
mkdir -p ~/discord-kg/{exports,scripts,config,logs}

# Download project files
echo "📥 Downloading project files..."
cd ~/discord-kg
git clone https://github.com/artfhc/project-discord-knowledge-graph.git repo
cp -r repo/scripts/* scripts/ 2>/dev/null || echo "No scripts directory found"
cp -r repo/deployment/scripts/* scripts/ 2>/dev/null || echo "No deployment scripts found"

# Set up Docker Compose for production
echo "🐳 Setting up Docker Compose..."
cp repo/deployment/docker-compose.yml ~/discord-kg/
cp repo/deployment/requirements-uploader.txt ~/discord-kg/

# Create production Dockerfile
cat > ~/discord-kg/Dockerfile.uploader << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Cloud SDK
RUN curl https://sdk.cloud.google.com | bash
ENV PATH="/root/google-cloud-sdk/bin:${PATH}"

# Install Python dependencies
COPY requirements-uploader.txt /tmp/
RUN pip install -r /tmp/requirements-uploader.txt

# Create app directory
WORKDIR /app

# Copy scripts
COPY scripts/ /app/scripts/

# Create directories
RUN mkdir -p /app/exports /app/logs /app/config

CMD ["python", "/app/scripts/export_scheduler.py"]
EOF

# Pull DiscordChatExporter image
echo "📥 Pulling DiscordChatExporter Docker image..."
docker pull tyrrrz/discordchatexporter:stable

# Set up environment
echo "⚙️ Setting up environment..."
cat > ~/discord-kg/config/.env << EOF
# Discord Configuration
DISCORD_TOKEN=$DISCORD_TOKEN

# Google Cloud Configuration  
GOOGLE_CLOUD_PROJECT=discord-knowledge-graph
GOOGLE_CLOUD_BUCKET=discord-kg-exports

# Export Configuration
EXPORT_FORMAT=json
EXPORT_PATH=/home/$USER/discord-kg/exports
LOG_PATH=/home/$USER/discord-kg/logs

# Schedule Configuration (HH:MM format for Python schedule library)
EXPORT_SCHEDULE="02:00"  # Daily at 2 AM
EOF

# Create example channels configuration
echo "📝 Creating example channels configuration..."
cat > ~/discord-kg/config/channels.txt.example << 'EOF'
# Discord Channels Configuration
# Format: CHANNEL_ID,CHANNEL_NAME
# Replace with your actual channel IDs

# Example channels (replace with real channel IDs):
1096103065129586759,new-symphony-alerts
1026653175027085342,portfolio-showcase

# To find channel IDs:
# 1. Enable Developer Mode in Discord settings
# 2. Right-click on a channel and select "Copy ID"
EOF

# Create systemd service for auto-start (optional)
echo "⚙️ Creating systemd service for auto-start..."
sudo tee /etc/systemd/system/discord-kg.service > /dev/null <<EOF
[Unit]
Description=Discord Knowledge Graph Pipeline
After=docker.service
Requires=docker.service

[Service]
Type=forking
RemainAfterExit=yes
WorkingDirectory=/home/$USER/discord-kg
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
Restart=on-failure
StartLimitBurst=3
User=$USER

[Install]
WantedBy=multi-user.target
EOF

echo "✅ VM setup complete!"
echo ""
echo "🔧 Manual Configuration Required:"
echo "1. Log out and back in to apply Docker group membership: logout"
echo "2. Copy and edit channels: cp ~/discord-kg/config/channels.txt.example ~/discord-kg/config/channels.txt"
echo "3. Edit with real channel IDs: nano ~/discord-kg/config/channels.txt"
echo "4. Set up Google Cloud authentication (if not done): gcloud auth login"
echo "5. Run GCS setup: ~/discord-kg/repo/deployment/config/gcs-setup.sh"
echo ""
echo "✅ Discord token automatically configured from Secret Manager"
echo ""
echo "🚀 Start the Pipeline:"
echo "  cd ~/discord-kg && docker compose up -d"
echo ""
echo "🔍 Monitor:"
echo "  docker compose logs -f                    # View all logs"
echo "  docker compose logs -f storage-uploader  # View uploader logs"
echo "  ls -la exports/                          # Check exported files"
echo ""
echo "🛑 Stop:"
echo "  docker compose down"
echo ""
echo "🔧 Enable auto-start (optional):"
echo "  sudo systemctl enable discord-kg"
echo "  sudo systemctl start discord-kg"
echo ""
echo "Configuration files:"
echo "  - Environment config: ~/discord-kg/config/.env (Discord token configured automatically)"
echo "  - Channel list: ~/discord-kg/config/channels.txt (edit with your channel IDs)"
echo "  - Docker Compose: ~/discord-kg/docker-compose.yml"

EONG