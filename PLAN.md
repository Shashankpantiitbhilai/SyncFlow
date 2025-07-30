# Zenskar Backend Assignment - Implementation Plan

## Project Overview
Building a two-way integration system between a custom customer catalog and Stripe, with extensible architecture for future integrations.

## System Architecture

### Core Components
1. **Customer Database** - PostgreSQL with customer table
2. **API Server** - FastAPI for REST endpoints and webhook handling
3. **Message Queue** - Apache Kafka for event-driven architecture
4. **Integration Services** - Modular sync services for external systems
5. **Background Workers** - Event processors for queue consumption

### Database Schema
```sql
-- customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- external_mappings table (for tracking external IDs)
CREATE TABLE external_mappings (
    id SERIAL PRIMARY KEY,
    internal_customer_id INTEGER REFERENCES customers(id),
    external_system VARCHAR(50) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(external_system, external_id)
);

-- sync_events table (for event tracking)
CREATE TABLE sync_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    external_system VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);
```

## Project Structure

```
zenskar-backend/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── customers.py     # Customer CRUD endpoints
│   │   │   └── webhooks.py      # Webhook endpoints
│   │   └── dependencies.py      # API dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── database.py         # Database connection
│   │   └── kafka_client.py     # Kafka producer/consumer
│   ├── models/
│   │   ├── __init__.py
│   │   ├── customer.py         # Customer model
│   │   ├── external_mapping.py # External mapping model
│   │   └── sync_event.py       # Sync event model
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── base.py            # Base integration interface
│   │   ├── stripe/
│   │   │   ├── __init__.py
│   │   │   ├── client.py      # Stripe API client
│   │   │   ├── sync.py        # Stripe sync logic
│   │   │   └── webhooks.py    # Stripe webhook handlers
│   │   └── salesforce/        # Future integration
│   │       ├── __init__.py
│   │       ├── client.py
│   │       └── sync.py
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── outbound_sync.py   # Outbound sync worker
│   │   ├── inbound_sync.py    # Inbound sync worker
│   │   └── base_worker.py     # Base worker class
│   └── utils/
│       ├── __init__.py
│       ├── logging.py         # Logging configuration
│       └── exceptions.py      # Custom exceptions
├── tests/
│   ├── __init__.py
│   ├── test_api/
│   ├── test_integrations/
│   └── test_workers/
├── docker/
│   ├── docker-compose.yml     # Full stack setup
│   ├── Dockerfile.api         # API service
│   └── Dockerfile.worker      # Worker service
├── migrations/
│   └── init.sql              # Database initialization
├── requirements.txt
├── .env.example
├── README.md
└── run.py                    # Application entry point
```

## Implementation Phases

### Phase 1: Core Infrastructure (Day 1-2)
1. **Database Setup**
   - Set up PostgreSQL database
   - Create customer and mapping tables
   - Set up database migrations

2. **Kafka Setup**
   - Configure Kafka using Docker
   - Create topics for customer events
   - Test producer/consumer functionality

3. **Basic API Server**
   - Set up FastAPI application
   - Implement customer CRUD endpoints
   - Add database connection and models

### Phase 2: Stripe Integration (Day 3-4)
1. **Stripe Client Setup**
   - Create Stripe test account
   - Implement Stripe API client
   - Handle authentication and error handling

2. **Outbound Sync (Product → Stripe)**
   - Implement event publishing on customer changes
   - Create outbound sync worker
   - Handle create/update/delete operations
   - Map internal IDs to Stripe customer IDs

3. **Inbound Sync (Stripe → Product)**
   - Set up webhook endpoint using ngrok
   - Implement webhook handlers for Stripe events
   - Process customer.created/updated/deleted events
   - Handle duplicate prevention and conflict resolution

### Phase 3: Queue Processing & Workers (Day 5)
1. **Event Processing**
   - Implement robust event processing
   - Add retry mechanisms for failed syncs
   - Implement dead letter queues
   - Add monitoring and logging

2. **Error Handling**
   - Implement comprehensive error handling
   - Add circuit breaker patterns
   - Handle rate limiting from external APIs
   - Implement event replay capabilities

### Phase 4: Testing & Documentation (Day 6-7)
1. **Testing**
   - Unit tests for all components
   - Integration tests for Stripe sync
   - End-to-end testing scenarios
   - Performance testing

2. **Documentation**
   - API documentation with Swagger
   - Deployment instructions
   - Configuration guide
   - Troubleshooting guide

## Key Technical Decisions

### 1. Event-Driven Architecture
- **Kafka Topics**: 
  - `customer.events` - All customer-related events
  - `sync.outbound` - Events for outbound synchronization
  - `sync.inbound` - Events for inbound synchronization

### 2. Integration Pattern
```python
class BaseIntegration(ABC):
    @abstractmethod
    async def create_customer(self, customer_data: dict) -> str:
        pass
    
    @abstractmethod
    async def update_customer(self, external_id: str, customer_data: dict) -> bool:
        pass
    
    @abstractmethod
    async def delete_customer(self, external_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_customer(self, external_id: str) -> dict:
        pass
```

### 3. Event Schema
```json
{
  "event_id": "uuid",
  "event_type": "customer.created|updated|deleted",
  "timestamp": "ISO 8601",
  "source": "internal|stripe|salesforce",
  "customer_data": {
    "id": "internal_id",
    "name": "customer_name",
    "email": "customer_email"
  },
  "external_mappings": {
    "stripe": "stripe_customer_id",
    "salesforce": "salesforce_contact_id"
  }
}
```

## Extensibility Plans

### Adding Salesforce Integration

1. **New Integration Module**
   ```python
   class SalesforceIntegration(BaseIntegration):
       def __init__(self, api_key: str, instance_url: str):
           self.client = SalesforceClient(api_key, instance_url)
       
       async def create_customer(self, customer_data: dict) -> str:
           # Implement Salesforce Contact creation
           pass
   ```

2. **Configuration Updates**
   - Add Salesforce credentials to config
   - Register new integration in worker factory
   - Update external_mappings table to track Salesforce IDs

3. **Webhook Support**
   - Add Salesforce webhook endpoints
   - Handle Salesforce-specific event formats
   - Map Salesforce Contact changes to internal events

### Supporting Other Catalogs (Invoices)

1. **Generic Catalog Framework**
   ```python
   class BaseCatalog(ABC):
       @abstractmethod
       def get_entity_type(self) -> str:
           pass
       
       @abstractmethod
       def get_sync_fields(self) -> List[str]:
           pass
   
   class InvoiceCatalog(BaseCatalog):
       def get_entity_type(self) -> str:
           return "invoice"
   ```

2. **Configurable Sync Rules**
   - Define field mappings between systems
   - Support for custom transformation rules
   - Conditional sync based on business rules

3. **Multi-Entity Workers**
   - Extend workers to handle multiple entity types
   - Route events based on entity type
   - Maintain separate sync states per entity

## Configuration Management

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/zenskar
DATABASE_POOL_SIZE=20

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_GROUP_ID=zenskar-sync

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Deployment Strategy

### Development Environment
```bash
# Start infrastructure
docker-compose up -d postgres kafka

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn src.api.main:app --reload

# Start workers
python -m src.workers.outbound_sync
python -m src.workers.inbound_sync
```

### Production Considerations
1. **Scalability**
   - Horizontal scaling of workers
   - Database connection pooling
   - Kafka partition strategy

2. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alert manager setup

3. **Security**
   - API authentication
   - Webhook signature verification
   - Secrets management

## Risk Mitigation

### 1. Data Consistency
- Implement idempotent operations
- Use database transactions
- Handle partial failures gracefully

### 2. Rate Limiting
- Implement exponential backoff
- Respect API rate limits
- Queue throttling mechanisms

### 3. Data Loss Prevention
- Persistent message queues
- Event sourcing for audit trail
- Regular backup strategies

## Success Metrics

1. **Sync Performance**
   - < 5 seconds for customer changes to propagate
   - 99.9% success rate for sync operations
   - < 1% duplicate events

2. **System Reliability**
   - 99.9% uptime for API services
   - Automatic recovery from failures
   - Zero data loss during sync

3. **Developer Experience**
   - < 1 hour to add new integration
   - Comprehensive test coverage (>90%)
   - Clear documentation and examples

This plan provides a solid foundation for building a scalable, maintainable two-way integration system that can easily be extended for future requirements.
