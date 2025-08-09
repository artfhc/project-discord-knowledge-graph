# Discord Knowledge Graph - Google Cloud Deployment

Complete deployment setup for running Discord exports on Google Cloud Platform with automated storage and processing.

## Quick Start

1. **Create GCP VM and configure environment:**
   ```bash
   # 1. Create the VM
   ./gcp-vm-create.sh
   
   # 2. SSH into the VM
   gcloud compute ssh discord-kg-vm --zone=us-central1-a
   
   # 3. Run the setup script
   curl -sSL https://raw.githubusercontent.com/yourusername/discord-kg/main/deployment/gcp-setup.sh | bash
   ```

2. **Configure Google Cloud Storage:**
   ```bash
   cd ~/discord-kg
   ./config/gcs-setup.sh
   ```

3. **Configure Discord channels:**
   ```bash
   # Copy and edit the channels configuration
   cp config/channels.txt.example config/channels.txt
   nano config/channels.txt  # Add your channel IDs
   
   # Add your Discord token
   echo "YOUR_DISCORD_TOKEN" > config/discord_token
   chmod 600 config/discord_token
   ```

4. **Deploy the services:**
   ```bash
   docker-compose up -d
   ```

## Architecture Overview

```
┌─────────────┐    ┌────────────────┐    ┌──────────────┐
│   Discord   │────│ DiscordChat    │────│   Google     │
│   Servers   │    │   Exporter     │    │ Cloud Storage│
└─────────────┘    └────────────────┘    └──────────────┘
                            │                     │
                   ┌────────▼────────┐           │
                   │   Scheduler     │           │
                   │   (Cron Jobs)   │           │
                   └─────────────────┘           │
                                                 │
┌─────────────┐    ┌────────────────┐           │
│  Knowledge  │◄───│   Processing   │◄──────────┘
│    Graph    │    │    Pipeline    │
└─────────────┘    └────────────────┘
```

## Configuration Files

- **`.env`**: Environment variables (Discord token, GCP settings)
- **`channels.txt`**: List of Discord channels to export
- **`gcp-service-account.json`**: GCP service account credentials
- **`docker-compose.yml`**: Container orchestration

## Automated Features

- **Scheduled Exports**: Daily exports at 2 AM (configurable)
- **Automatic Upload**: Exports automatically uploaded to GCS
- **Health Monitoring**: System health checks every 6 hours
- **Log Management**: Centralized logging with rotation
- **Error Handling**: Retry logic and failure notifications

## Storage Structure

```
gs://your-bucket/
├── discord-exports/
│   ├── 20240109_020000/
│   │   ├── general_123456789.json
│   │   ├── trading_234567890.json
│   │   └── manifest.json
│   └── 20240108_020000/
│       └── ...
└── processed/
    ├── knowledge-graph/
    └── metrics/
```

## Monitoring & Logs

- **Application logs**: `/home/user/discord-kg/logs/`
- **Docker logs**: `docker-compose logs -f`
- **System monitoring**: Health check reports every 6 hours

## Costs Estimation

- **VM Instance (e2-small)**: ~$15/month
- **Storage (50GB)**: ~$2/month
- **Network egress**: ~$1-3/month
- **Total**: ~$18-20/month

## Security Features

- Service account with minimal required permissions
- Token stored in secure file with restricted permissions
- Network security groups configured
- Automatic lifecycle management for old exports

## Troubleshooting

### Common Issues

1. **Permission denied for Discord token:**
   ```bash
   chmod 600 ~/discord-kg/config/discord_token
   ```

2. **GCS upload failures:**
   ```bash
   # Check service account permissions
   gsutil iam get gs://your-bucket
   ```

3. **Docker container not starting:**
   ```bash
   docker-compose logs discord-exporter
   ```

### Manual Export

To run a manual export:
```bash
docker-compose exec discord-exporter /app/scripts/export_discord.sh
```

### View Export Status

```bash
# Check recent exports
gsutil ls gs://your-bucket/discord-exports/

# View logs
tail -f ~/discord-kg/logs/scheduler.log
```