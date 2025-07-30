# 🔑 Stripe Configuration Guide

## Step-by-Step Instructions to Get Your Stripe Secrets

### 1. 📋 **Get Stripe API Key** (Already Done ✅)
Your current Stripe secret key in `.env`:
```
STRIPE_SECRET_KEY=sk_test_51RqHNx3mIkQC8ZPhrc26mZBGkHWBemOerzcS5dtqMEQBWhTqAC7fcSqN6VPFCSo9zyeeZ0xJbV5nQfTTwJcCYtJD00oayY8bAn
```
This looks correct! ✅

### 2. 🌐 **Set Up ngrok for Webhook Development**

#### Install ngrok (Already Done ✅)
The ngrok executable is now in your project directory.

#### Start ngrok tunnel:
```bash
# In a new terminal window, run:
./ngrok http 8000
```

This will show output like:
```
Forwarding    https://abc123def.ngrok.io -> http://localhost:8000
```

**Copy the HTTPS URL** (e.g., `https://abc123def.ngrok.io`)

### 3. 🔗 **Create Stripe Webhook**

1. **Go to Stripe Dashboard**:
   - Visit: https://dashboard.stripe.com
   - Make sure you're in **Test mode** (toggle at top-left)

2. **Navigate to Webhooks**:
   - Left sidebar → **Developers** → **Webhooks**

3. **Add Endpoint**:
   - Click **"Add endpoint"**
   - **Endpoint URL**: `https://YOUR-NGROK-URL.ngrok.io/api/v1/webhooks/stripe`
   - Example: `https://abc123def.ngrok.io/api/v1/webhooks/stripe`

4. **Select Events**:
   - Click **"Select events"**
   - Choose these events:
     - ✅ `customer.created`
     - ✅ `customer.updated` 
     - ✅ `customer.deleted`
   - Click **"Add events"**

5. **Create Endpoint**:
   - Click **"Add endpoint"**

6. **Get Webhook Secret**:
   - After creation, click on your new webhook
   - In the webhook details, find **"Signing secret"**
   - Click **"Reveal"** 
   - Copy the secret (starts with `whsec_`)

### 4. 📝 **Update Your .env File**

Replace these values in your `.env` file:

```bash
# Replace with your ngrok URL
WEBHOOK_BASE_URL=https://YOUR-NGROK-URL.ngrok.io

# Replace with your actual webhook secret from Stripe
STRIPE_WEBHOOK_SECRET=whsec_your_actual_webhook_secret_here
```

### 5. 🔄 **About Stripe API Version**

The API version `2023-10-16` is fine to keep. This is:
- ✅ A stable, recent version of Stripe API
- ✅ Compatible with the customer endpoints we're using
- ✅ No need to change unless you want the latest features

**Available versions**: You can see all available versions at:
https://stripe.com/docs/api/versioning

**Current latest**: `2024-06-20` (but `2023-10-16` works perfectly)

### 6. ✅ **Complete Example .env**

Your `.env` should look like this after setup:

```bash
# Database Configuration
DATABASE_URL=postgresql://zenskar_user:zenskar_pass@localhost:5432/zenskar_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=0

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_GROUP_ID=zenskar-sync
KAFKA_AUTO_OFFSET_RESET=earliest

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_51RqHNx3mIkQC8ZPhrc26mZBGkHWBemOerzcS5dtqMEQBWhTqAC7fcSqN6VPFCSo9zyeeZ0xJbV5nQfTTwJcCYtJD00oayY8bAn
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdef...    # ← Replace with actual secret
STRIPE_API_VERSION=2023-10-16

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Webhook Configuration
WEBHOOK_BASE_URL=https://abc123def.ngrok.io    # ← Replace with your ngrok URL

# Environment
ENVIRONMENT=development
```

## 🚀 **Quick Setup Commands**

### Terminal 1: Start ngrok
```bash
./ngrok http 8000
```

### Terminal 2: Start Infrastructure
```bash
docker-compose up -d postgres kafka
```

### Terminal 3: Start API Server
```bash
python run.py
```

### Terminal 4: Test Webhook
```bash
# Test that webhook endpoint is accessible
curl https://YOUR-NGROK-URL.ngrok.io/api/v1/webhooks/stripe
```

## 🔍 **Troubleshooting**

### ngrok Issues:
- **Problem**: ngrok not starting
- **Solution**: Make sure port 8000 is free, restart ngrok

### Webhook Issues:
- **Problem**: Webhook not receiving events
- **Solution**: 
  1. Check ngrok URL is correct in Stripe
  2. Verify API server is running on port 8000
  3. Check webhook signature validation

### Testing Webhook:
```bash
# Create a test customer in Stripe dashboard
# Check your API logs to see if webhook was received
```

## 📱 **Next Steps**

1. ✅ Set up ngrok tunnel
2. ✅ Create Stripe webhook 
3. ✅ Update `.env` with webhook secret
4. ✅ Test the integration by creating a customer in Stripe Dashboard
5. ✅ Check your local API logs for incoming webhook events

You're all set! 🎉
