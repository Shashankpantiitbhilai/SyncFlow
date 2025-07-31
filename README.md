# Zenskar Two-Way Integration System

A real-time customer data synchronization system built for Zenskar's Backend Engineer Intern ## 🐳 Docker Container Architecturessignment. This project demonstrates bidirectional integration between an internal customer catalog and Stripe, with event-driven architecture using Kafka.

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
        API[FastAPI Server]
        DB[(PostgreSQL)]
        Worker[Background Workers]
    end
    
    subgraph "Message Queue"
        Kafka[Kafka Broker]
        OutTopic[sync.outbound]
        InTopic[sync.inbound]
    end
    
    subgraph "External Systems"
        Stripe[Stripe API]
        Webhook[Webhook Handler]
    end
    
    API --> DB
    API --> OutTopic
    OutTopic --> Worker
    Worker --> Stripe
    Stripe --> Webhook
    Webhook --> InTopic
    InTopic --> Worker
    Worker --> DB
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- ngrok (for webhook forwarding)
- Stripe test account

### 1. Clone and Setup
```bash
git clone <your-repository>
cd zenskar-backend-assignment
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` file with your Stripe credentials:
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
graph TB
    subgraph "Docker Network: zenskar-network"
        API[zenskar-api<br/>FastAPI Server<br/>Port: 8000]
        WORKER[zenskar-worker<br/>Background Processor<br/>Internal]
        DB[(zenskar-postgres<br/>PostgreSQL Database<br/>Port: 5432)]
        KAFKA[zenskar-kafka<br/>Message Broker<br/>Port: 9093]
        ZK[zenskar-zookeeper<br/>Coordination Service<br/>Port: 2181]
        SETUP[kafka-setup<br/>Initialization Service<br/>Ephemeral]
    end
    
    API -->|TCP/SQL| DB
    API -->|TCP/Protocol| KAFKA
    WORKER -->|TCP/Protocol| KAFKA
    WORKER -->|TCP/SQL| DB
    KAFKA -->|TCP| ZK
    SETUP -->|Admin API| KAFKA
```

### Container Interaction Flow

```mermaid
sequenceDiagram
    participant Client as External Client
    participant API as zenskar-api
    participant DB as zenskar-postgres
    participant KP as Kafka Producer
    participant KT as Kafka Topics
    participant KC as Kafka Consumer
    participant Worker as zenskar-worker
    participant Stripe as Stripe API

    Note over Client,Stripe: Container Interaction During Customer Creation
    
    Client->>API: HTTP POST /customers
    API->>DB: SQL INSERT customer
    DB-->>API: customer_id
    API->>KP: Publish event
    KP->>KT: sync.outbound message
    API-->>Client: HTTP 201 Response
    
    Note over KT,Worker: Asynchronous Processing
    
    KT->>KC: Consume message
    KC->>Worker: Process event
    Worker->>Stripe: HTTP POST customer
    Stripe-->>Worker: stripe_customer_id
    Worker->>DB: INSERT external_mapping
    DB-->>Worker: Confirmation
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

### Operational Considerations

#### Container Restart Behavior
- **Database**: Persistent volumes ensure data survival across restarts
- **Kafka**: Topic metadata and message retention survive restarts
- **API/Worker**: Stateless containers restart cleanly
- **ZooKeeper**: Maintains Kafka coordination state

#### Scaling Characteristics
- **API Container**: Horizontally scalable with load balancer
- **Worker Container**: Scalable through Kafka consumer groups
- **Database**: Single instance with backup/replication strategies
- **Kafka**: Single node sufficient for development, clusterable for production

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
    participant U as User/Client
    participant API as FastAPI Server
    participant DB as PostgreSQL
    participant KC as Kafka Producer
    participant KT as Kafka Topic
    participant OW as Outbound Worker
    participant S as Stripe API
    participant EM as External Mapping

    U->>API: POST /api/v1/customers
    Note over API: Validate request data
    
    API->>DB: INSERT INTO customers
    DB-->>API: customer_id = 10
    
    API->>KC: publish_message()
    Note over KC: Topic: sync.outbound
    KC->>KT: {"event_type": "customer.created", "entity_id": 10, "customer_data": {...}}
    
    API-->>U: 201 Created {"id": 10, ...}
    
    Note over KT,OW: Background Processing
    KT->>OW: consume_message()
    Note over OW: OutboundSyncWorker.process_message()
    
    OW->>DB: SELECT customer WHERE id = 10
    DB-->>OW: customer data
    
    OW->>DB: INSERT INTO sync_events (status='pending')
    
    OW->>S: stripe.Customer.create(name, email, metadata)
    S-->>OW: {"id": "cus_xyz123", ...}
    
    OW->>EM: INSERT INTO external_mappings
    Note over EM: internal_id=10, external_id=cus_xyz123
    
    OW->>DB: UPDATE sync_events (status='completed')
    
    Note over S: Customer now exists in Stripe!
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
    participant SD as Stripe Dashboard
    participant S as Stripe System
    participant N as Ngrok Tunnel
    participant WH as Webhook Handler
    participant KC as Kafka Producer
    participant KT as Kafka Topic
    participant IW as Inbound Worker
    participant DB as PostgreSQL
    participant EM as External Mapping

    Note over SD: User creates customer manually
    SD->>S: Create customer via Stripe UI
    S->>S: Customer created: cus_abc456
    
    Note over S,N: Webhook Delivery
    S->>N: POST webhook event
    Note over N: Forwards to localhost:8000
    N->>WH: POST /api/v1/webhooks/stripe
    
    Note over WH: Verify webhook signature
    WH->>WH: stripe.Webhook.construct_event()
    
    WH->>KC: publish_message()
    Note over KC: Topic: sync.inbound
    KC->>KT: {"source": "stripe", "event_type": "customer.created", "data": {...}}
    
    WH-->>S: 200 OK (Webhook acknowledged)
    
    Note over KT,IW: Background Processing
    KT->>IW: consume_message()
    Note over IW: InboundSyncWorker.process_message()
    
    IW->>EM: SELECT mapping WHERE external_id = 'cus_abc456'
    EM-->>IW: No mapping found
    
    IW->>DB: INSERT INTO customers (name, email)
    DB-->>IW: customer_id = 11
    
    IW->>EM: INSERT INTO external_mappings
    Note over EM: internal_id=11, external_id=cus_abc456
    
    IW->>DB: INSERT INTO sync_events (status='completed')
    
    Note over DB: Customer now synced to internal system!
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
    participant OW as Outbound Worker
    participant S as Stripe API
    participant DB as PostgreSQL
    participant KT as Kafka Topic

    OW->>S: stripe.Customer.create()
    S-->>OW: 429 Rate Limited
    
    Note over OW: Catch RateLimitError
    OW->>DB: UPDATE sync_events (status='failed', retry_count++)
    
    Note over OW: Exponential backoff
    OW->>OW: sleep(2^retry_count)
    
    OW->>S: Retry stripe.Customer.create()
    S-->>OW: 200 Success
    
    OW->>DB: UPDATE sync_events (status='completed')
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


