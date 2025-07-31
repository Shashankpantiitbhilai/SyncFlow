# Zenskar Two-Way Integration System

A real-time customer data synchronization system built for Zenskar's Backend Engineer Intern This project demonstrates bidirectional integration between an internal customer catalog and Stripe, with event-driven architecture using Kafka.

## 🎯 Project Overview

This system implements a two-way sync between your internal customer database and Stripe's customer catalog. Changes in either system are automatically propagated to the other in near real-time using webhooks and background workers.

## ✅ Assignment Requirements Completed

### ✅ Core Requirements
- [x] **Customer Table**: PostgreSQL with ID, name, email columns
- [x] **Stripe Integration**: Free test account with two-way sync
- [x] **Kafka Queue**: Docker-based event processing
- [x] **Outbound Sync**: Internal → Stripe via background workers
- [x] **Inbound Sync**: Stripe → Internal via webhooks (ngrok)
- [x] **Extensible Architecture**: Ready for Salesforce and other integrations

### ✅ Technical Implementation
- [x] **FastAPI**: REST API with CRUD operations
- [x] **PostgreSQL**: Relational database with proper schema
- [x] **Kafka**: Event streaming and message queues
- [x] **Docker**: Containerized deployment
- [x] **Webhook Processing**: Real-time event handling
- [x] **Error Handling**: Retry logic and status tracking
- [x] **Monitoring**: Comprehensive logging and status tracking

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Internal System"
        API[FastAPI Server]:::apiStyle
        DB[(PostgreSQL)]:::dbStyle
        Worker[Background Workers]:::workerStyle
    end
    
    subgraph "Message Queue"
        Kafka[Kafka Broker]:::kafkaStyle
        OutTopic[sync.outbound]:::topicStyle
        InTopic[sync.inbound]:::topicStyle
    end
    
    subgraph "External Systems"
        Stripe[Stripe API]:::stripeStyle
        Webhook[Webhook Handler]:::webhookStyle
    end
    
    API --> DB
    API --> OutTopic
    OutTopic --> Worker
    Worker --> Stripe
    Stripe --> Webhook
    Webhook --> InTopic
    InTopic --> Worker
    Worker --> DB

    classDef apiStyle fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    classDef dbStyle fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    classDef workerStyle fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    classDef kafkaStyle fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff
    classDef topicStyle fill:#E91E63,stroke:#AD1457,stroke-width:2px,color:#fff
    classDef stripeStyle fill:#6772E5,stroke:#4C63D2,stroke-width:2px,color:#fff
    classDef webhookStyle fill:#00BCD4,stroke:#00838F,stroke-width:2px,color:#fff
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- ngrok (for webhook forwarding)
- Stripe test account

### 1. Clone and Setup
```bash
git clone https://github.com/Shashankpantiitbhilai/zenskar-backend-assignment.git
cd zenskar-backend-assignment
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` file with  Stripe credentials:
```env
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### 3. Start the System
```bash
# Start all services
docker-compose up -d

# Check if services are running
docker-compose ps
```

### 4. Set Up Webhook Forwarding
```bash
# Start ngrok to expose local server
ngrok http 8000

# Note the ngrok URL (e.g., https://abc123.ngrok.io)
# Add webhook in Stripe Dashboard:
# URL: https://abc123.ngrok.io/api/v1/webhooks/stripe
# Events: customer.created, customer.updated, customer.deleted
```

### 5. Test the Integration

#### API Health Check
```bash
curl http://localhost:8000/health
```

#### Create Customer (Outbound Sync)
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe", 
    "email": "john.doe@example.com"
  }'
```

#### List Customers
```bash
curl http://localhost:8000/api/v1/customers
```

#### Watch the Sync Process
```bash
# Monitor worker logs
docker logs -f zenskar-worker

# Monitor API logs
docker logs -f zenskar-api
```

## � How Docker Containers Work Together

The system deploys as a distributed microservices architecture using Docker Compose, with six containers orchestrated to provide event-driven two-way synchronization between internal systems and Stripe.

### Container Topology

```mermaid
graph LR
    subgraph Docker["🐳 Docker Network"]
        API[🚀 API<br/>Port: 8000]:::api
        WORKER[⚙️ Worker<br/>Background]:::worker
        DB[(🗄️ Database<br/>Port: 5432)]:::db
        KAFKA[📨 Kafka<br/>Port: 9093]:::kafka
        ZK[🔧 ZooKeeper<br/>Port: 2181]:::zk
        SETUP[⚡ Setup<br/>Init Only]:::setup
    end
    
    API --> DB
    API --> KAFKA
    WORKER --> KAFKA
    WORKER --> DB
    KAFKA --> ZK
    SETUP -.-> KAFKA

    classDef api fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff
    classDef worker fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff
    classDef db fill:#2196F3,stroke:#1565C0,stroke-width:2px,color:#fff
    classDef kafka fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff
    classDef zk fill:#795548,stroke:#5D4037,stroke-width:2px,color:#fff
    classDef setup fill:#607D8B,stroke:#455A64,stroke-width:2px,color:#fff
```

### Container Interaction Flow

```mermaid
sequenceDiagram
    participant Client as 👤 Client
    participant API as 🚀 API
    participant DB as 🗄️ Database
    participant Kafka as � Kafka
    participant Worker as ⚙️ Worker
    participant Stripe as 💳 Stripe

    Client->>API: Create Customer
    API->>DB: Save Customer
    API->>Kafka: Publish Event
    Kafka->>Worker: Process Event
    Worker->>Stripe: Sync to Stripe
    Worker->>DB: Update Mapping
```

### Container Specifications

#### API Container (zenskar-api)
- **Function**: HTTP REST API server and webhook endpoint
- **Technology**: FastAPI with Uvicorn ASGI server
- **Network**: Exposes port 8000 for external traffic
- **Dependencies**: PostgreSQL for persistence, Kafka for event publishing
- **Resource Profile**: CPU-bound during request processing, moderate memory usage

```bash
# Monitor API container
docker logs -f zenskar-api
docker stats zenskar-api
```

#### Worker Container (zenskar-worker)
- **Function**: Background event processor for sync operations
- **Technology**: Kafka consumer with Python asyncio
- **Network**: Internal only, no exposed ports
- **Dependencies**: Kafka for event consumption, PostgreSQL for state updates, Stripe API
- **Resource Profile**: I/O-bound with periodic CPU spikes during sync operations

```bash
# Monitor worker processing
docker logs -f zenskar-worker
```

#### Database Container (zenskar-postgres)
- **Function**: Primary data persistence layer
- **Technology**: PostgreSQL 14 with initialized schema
- **Network**: Port 5432 exposed for development access
- **Persistence**: Volume-mounted data directory for durability
- **Resource Profile**: Memory-intensive for caching, I/O-bound for queries

```bash
# Access database directly
docker exec -it zenskar-postgres psql -U zenskar_user -d zenskar_db
```

#### Message Broker Container (zenskar-kafka)
- **Function**: Event streaming and message queue management
- **Technology**: Apache Kafka with KRaft mode
- **Network**: Port 9093 exposed for external producer/consumer access
- **Topics**: sync.inbound, sync.outbound
- **Resource Profile**: Network and disk I/O intensive, moderate CPU usage

```bash
# Monitor Kafka topics and messages
docker exec -it zenskar-kafka kafka-topics --bootstrap-server localhost:9093 --list
docker exec -it zenskar-kafka kafka-console-consumer --bootstrap-server localhost:9093 --topic sync.outbound
```

#### Coordination Container (zenskar-zookeeper)
- **Function**: Kafka cluster coordination and metadata management
- **Technology**: Apache ZooKeeper
- **Network**: Port 2181 for Kafka coordination protocol
- **Resource Profile**: Low resource usage, critical for Kafka stability

#### Initialization Container (kafka-setup)
- **Function**: One-time Kafka topic creation during startup
- **Lifecycle**: Ephemeral - exits after successful topic creation
- **Status**: Shows as "Exited (0)" in docker-compose ps - this is expected behavior

### Inter-Container Communication

#### Service Discovery
Containers communicate using Docker's internal DNS resolution:
- Database connection: `postgresql://zenskar_user:password@postgres:5432/zenskar_db`
- Kafka broker: `kafka:9093`
- Internal network: `zenskar-network` bridge

#### Startup Dependencies
The docker-compose configuration enforces startup ordering:
1. `zenskar-zookeeper` - Base coordination service
2. `zenskar-kafka` - Requires ZooKeeper for bootstrap
3. `kafka-setup` - Creates topics after Kafka is ready
4. `zenskar-postgres` - Independent database startup
5. `zenskar-api` & `zenskar-worker` - Require both database and Kafka

#### Health Check Strategy
```bash
# Verify all containers are operational
docker-compose ps

# Check container health and logs
docker logs zenskar-api | tail -20
docker logs zenskar-worker | tail -20

# Monitor resource utilization
docker stats --no-stream
```

#### Network Security
- Internal communication secured within Docker bridge network
- Only API container exposes public interface
- Database access restricted to internal containers
- Kafka access limited to producer/consumer containers

## �📊 System Components

### API Server (`src/api/`)
- **FastAPI** REST API server
- **Customer CRUD** operations
- **Webhook handlers** for Stripe events
- **Event publishing** to Kafka

### Background Workers (`src/workers/`)
- **Outbound Sync Worker**: Processes internal changes → Stripe
- **Inbound Sync Worker**: Processes Stripe changes → Internal DB
- **Error handling** and retry logic

### Integration Layer (`src/integrations/`)
- **Base Integration Interface**: Abstract class for all integrations
- **Stripe Integration**: Concrete implementation for Stripe API
- **Extensible design** for adding more integrations

### Data Models (`src/models/`)
- **Customer**: Core customer entity
- **External Mapping**: Links internal IDs with external system IDs
- **Sync Event**: Tracks synchronization status and history

## 🔄 Sync Flow Details

### Outbound Sync (Internal → Stripe)

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant API as 🚀 API
    participant DB as 🗄️ Database
    participant Kafka as 📨 Kafka
    participant Worker as ⚙️ Worker
    participant Stripe as � Stripe

    User->>API: POST /customers
    API->>DB: Save Customer
    DB-->>API: customer_id: 10
    API->>Kafka: Publish Event
    API-->>User: 201 Created
    
    Note over Kafka,Worker: Background Processing
    
    Kafka->>Worker: Consume Event
    Worker->>Stripe: Create Customer
    Stripe-->>Worker: stripe_id: cus_xyz123
    Worker->>DB: Save Mapping (10 ↔ cus_xyz123)
```

**Detailed Backend Flow:**
1. **API Layer**: Receives HTTP request, validates data
2. **Database Transaction**: Saves customer to PostgreSQL with auto-generated ID
3. **Event Publishing**: Publishes event to Kafka `sync.outbound` topic
4. **Worker Processing**: OutboundSyncWorker consumes event asynchronously
5. **External API Call**: Worker calls Stripe API to create customer
6. **Mapping Storage**: Stores internal↔external ID mapping
7. **Status Tracking**: Updates sync event status for monitoring

### Inbound Sync (Stripe → Internal)

```mermaid
sequenceDiagram
    participant Stripe as 💳 Stripe
    participant Webhook as � Webhook
    participant API as � API
    participant Kafka as 📨 Kafka
    participant Worker as ⚙️ Worker
    participant DB as 🗄️ Database

    Note over Stripe: Customer created in Stripe Dashboard
    
    Stripe->>Webhook: Send Webhook Event
    Webhook->>API: POST /webhooks/stripe
    API->>Kafka: Publish Event
    API-->>Webhook: 200 OK
    
    Note over Kafka,Worker: Background Processing
    
    Kafka->>Worker: Consume Event
    Worker->>DB: Save Customer
    Worker->>DB: Save Mapping (stripe_id ↔ internal_id)
```

**Detailed Backend Flow:**
1. **External Change**: Customer created/updated in Stripe dashboard
2. **Webhook Delivery**: Stripe sends HTTP POST to ngrok URL
3. **Signature Verification**: Webhook handler verifies Stripe signature
4. **Event Publishing**: Publishes verified event to Kafka `sync.inbound` topic
5. **Worker Processing**: InboundSyncWorker consumes event asynchronously
6. **Mapping Check**: Checks if customer already exists via external mapping
7. **Database Update**: Creates/updates customer in internal database
8. **Mapping Creation**: Creates new mapping if customer is new
9. **Status Tracking**: Records sync event for monitoring

### Error Handling Flow

```mermaid
sequenceDiagram
    participant Worker as ⚙️ Worker
    participant Stripe as 💳 Stripe
    participant DB as 🗄️ Database

    Worker->>Stripe: Create Customer
    Stripe-->>Worker: ❌ Rate Limited (429)
    
    Worker->>DB: Mark as Failed
    Worker->>Worker: Wait & Retry
    Worker->>Stripe: Create Customer (Retry)
    Stripe-->>Worker: ✅ Success (200)
    Worker->>DB: Mark as Completed
```

**Error Scenarios Handled:**
- **Rate Limiting**: Exponential backoff retry
- **Network Timeouts**: Automatic retry with backoff
- **Invalid Data**: Log error and skip (no retry)
- **Webhook Verification**: Reject invalid signatures
- **Duplicate Events**: Idempotency checks prevent duplicates

### Adding New Features
1. **Models**: Add new SQLAlchemy models in `src/models/`
2. **API Routes**: Add endpoints in `src/api/routes/`
3. **Workers**: Create workers in `src/workers/`
4. **Integrations**: Add integrations in `src/integrations/`

## 🚀 Future Extensions

### 1. Salesforce Integration Plan

The current architecture is designed to easily support additional integrations:

```python
# src/integrations/salesforce/client.py
class SalesforceIntegration(BaseIntegration):
    def __init__(self):
        super().__init__("salesforce")
        # Salesforce-specific initialization
    
    async def create_customer(self, customer_data):
        # Salesforce API implementation
        pass
```

**Steps to implement:**
1. Create `SalesforceIntegration` class extending `BaseIntegration`
2. Add Salesforce-specific configuration
3. Create Salesforce-specific workers
4. Add new Kafka topics for Salesforce events
5. Update external mappings to support multiple systems

### 2. Invoice Catalog Extension Plan

The system can be extended to support other entities like invoices:

```python
# New models
class Invoice(Base):
    id: int
    customer_id: int
    amount: decimal
    status: str

class InvoiceMapping(Base):
    internal_invoice_id: int
    external_system: str
    external_id: str
```

**Steps to implement:**
1. Create invoice models and database tables
2. Add invoice-specific Kafka topics (`invoice.sync.inbound`, `invoice.sync.outbound`)
3. Create invoice workers similar to customer workers
4. Extend integration interfaces to support invoices
5. Add invoice API endpoints

### 3. Multi-System Support

The current mapping system already supports multiple external systems:

```sql
-- External mappings table supports multiple systems
CREATE TABLE external_mappings (
    internal_customer_id INT,
    external_system VARCHAR,  -- 'stripe', 'salesforce', etc.
    external_id VARCHAR
);
```

## 🔒 Security Considerations

- **Webhook Verification**: All Stripe webhooks are verified using webhook secrets
- **Environment Variables**: Sensitive data stored in environment variables
- **API Keys**: Stripe keys are test keys, rotate for production
- **Database**: PostgreSQL with proper connection pooling

## 📝 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/db` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | `kafka:9093` |
| `STRIPE_SECRET_KEY` | Stripe API secret key | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | `whsec_...` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |

## 🎯 Performance Considerations

- **Async Processing**: All I/O operations are asynchronous
- **Connection Pooling**: Database connections are pooled
- **Event Processing**: Workers process events in parallel
- **Error Handling**: Comprehensive retry logic with exponential backoff
- **Monitoring**: Detailed logging for debugging and monitoring

## Assignment Summary

This project successfully implements all requirements for the Zenskar Backend Engineer Intern assignment:

✅ **Customer table** with PostgreSQL  
✅ **Stripe integration** with test account  
✅ **Kafka queue** for event processing  
✅ **Outbound sync** with background workers  
✅ **Inbound sync** with webhook handling  
✅ **Extensible architecture** for future integrations  
✅ **Comprehensive documentation** and deployment instructions  

The system demonstrates real-time bidirectional synchronization with proper error handling, monitoring, and a scalable architecture ready for production use.


