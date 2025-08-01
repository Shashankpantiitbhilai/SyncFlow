# 🚀 Installation Guide


This guide will walk through setting up the Zenskar Two-Way Integration System on your local machine.

## 📋 Prerequisites

Before starting, ensure you have the following installed:

- **Docker & Docker Compose** (v20.10 or higher)
- **ngrok** - For webhook forwarding
- **Git** - For cloning the repository
- **Stripe Test Account** - Free account for testing

### Installing Prerequisites

#### Docker Installation
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# macOS (using Homebrew)
brew install docker docker-compose

# Windows
# Download Docker Desktop from https://docker.com/products/docker-desktop
```

#### ngrok Installation
```bash
# macOS
brew install ngrok

# Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Windows
# Download from https://ngrok.com/download
```

## 🔧 System Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Shashankpantiitbhilai/zenskar-backend-assignment.git
cd zenskar-backend-assignment
```

### 2️⃣ Environment Configuration

Create environment file from template:
```bash
cp .env.example .env
```

Update `.env` with your configuration:

### 3️⃣ Stripe Account Setup

1. **Create Stripe Test Account**
   - Go to [Stripe Dashboard](https://dashboard.stripe.com/register)
   - Sign up for a free account
   - Note: Use "US" as country if facing issues

2. **Get API Keys**
   - Navigate to **Developers** → **API Keys**
   - Copy **Secret Key** (starts with `sk_test_`)

   - Update these in your `.env` file

### 4️⃣ Container Deployment

Start all services using Docker Compose:
```bash
# Build and start all containers
docker-compose up -d

# Verify all services are running
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
zenskar-api         Up                  0.0.0.0:8000->8000/tcp
zenskar-worker      Up                  
zenskar-postgres    Up                  0.0.0.0:5432->5432/tcp
zenskar-kafka       Up                  0.0.0.0:9093->9093/tcp
zenskar-zookeeper   Up                  0.0.0.0:2181->2181/tcp
zenskar-setup       Exited (0)          
```

### 5️⃣ Webhook Configuration

#### Start ngrok
```bash
# In a new terminal, start ngrok
ngrok http 8000
```

You'll see output like:
```
Forwarding    https://d4ea7e4659e8.ngrok-free.app -> http://localhost:8000
```

#### Configure Stripe Webhook

1. **Go to Stripe Dashboard**
   - Navigate to **Developers** → **Webhooks**
   - Click **Add endpoint**

2. **Add Webhook Endpoint**
   - **Endpoint URL**: `https://your-ngrok-url.ngrok-free.app/api/v1/webhooks/stripe`
   - **Events to send**: Select these events:
     - `customer.created`
     - `customer.updated` 
     - `customer.deleted`

3. **Get Webhook Secret**
   - After creating the webhook, click on it
   - In the **Signing secret** section, click **Reveal**
   - Copy the secret (starts with `whsec_`)
   - Update `STRIPE_WEBHOOK_SECRET` in your `.env` file

4. **Restart Services** (after updating .env)
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## 🔍 Verification

### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Database Connection
```bash
# Access PostgreSQL directly
docker exec -it zenskar-postgres psql -U zenskar_user -d zenskar_db

# List tables
\dt

# Expected tables: customers, external_mappings, sync_events
```

### Kafka Topics
```bash
# List Kafka topics
docker exec -it zenskar-kafka kafka-topics --bootstrap-server localhost:9093 --list

# Expected topics: sync.inbound, sync.outbound
```

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
sudo kill -9 <PID>
```

#### Docker Permission Issues (Linux)
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or restart terminal
```

#### Stripe Webhook Not Receiving Events
1. Ensure ngrok is running and forwarding to port 8000
2. Check that webhook URL in Stripe matches ngrok URL exactly
3. Verify webhook secret is correctly set in `.env`
4. Check API logs: `docker logs -f zenskar-api`

#### Database Connection Issues
```bash
# Check PostgreSQL logs
docker logs zenskar-postgres

# Restart PostgreSQL container
docker-compose restart zenskar-postgres
```

#### Kafka Connection Issues
```bash
# Check Kafka logs
docker logs zenskar-kafka

# Restart Kafka services
docker-compose restart zenskar-kafka zenskar-zookeeper
```

### Service Status Monitoring

```bash
# Monitor all container logs
docker-compose logs -f

# Monitor specific service
docker logs -f zenskar-api
docker logs -f zenskar-worker

# Check container resource usage
docker stats
```

## 🔄 Restart Services

```bash
# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Rebuild and restart (after code changes)
docker-compose up -d --build
```
