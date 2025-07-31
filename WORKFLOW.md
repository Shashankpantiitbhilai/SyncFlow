# Zenskar Backend System Workflow

## System Architecture Overview

The system consists of 5 main containers that work together to provide a robust two-way synchronization between internal customer data and external systems (like Stripe):

### 1. PostgreSQL Database (zenskar-postgres)
- **Container**: `postgres:15`
- **Port**: 5432
- **Purpose**:
  - Stores the core customer data
  - Maintains external system mappings
  - Tracks synchronization events
- **Key Tables**:
  - `customers`: Core customer information (id, name, email)
  - `external_mappings`: Links internal customer IDs to external system IDs (with source system)
  - `sync_events`: Tracks sync operations with full event history and status

### 2. Apache Kafka (zenskar-kafka)
- **Container**: `confluentinc/cp-kafka:7.4.0`
- **Port**: 9092
- **Purpose**:
  - Message broker for async event processing
  - Ensures reliable message delivery
  - Handles event queuing for sync operations
- **Key Topics**:
  - `sync.outbound`: Events for changes to be synced to external systems
  - `sync.inbound`: Events received from external system webhooks
- **Message Structure**:
  - Event type (created/updated/deleted)
  - Source system identifier
  - Customer data payload
  - Metadata (timestamps, correlation IDs)

### 3. ZooKeeper (zenskar-zookeeper)
- **Container**: `bitnami/zookeeper:3.8`
- **Port**: 2181
- **Purpose**:
  - Manages Kafka cluster state
  - Handles broker coordination
  - Maintains configuration information

### 4. API Server (zenskar-api)
- **Container**: `zenskar-backend-api`
- **Port**: 8000
- **Purpose**:
  - Exposes REST APIs for customer management
  - Handles incoming webhook events from Stripe
  - Publishes changes to Kafka for async processing
- **Key Endpoints**:
  - `POST /customers`: Create new customers
  - `PUT /customers/{id}`: Update customer information
  - `POST /webhooks/stripe`: Handle Stripe webhook events

### 5. Worker (zenskar-worker)
- **Container**: `zenskar-backend-worker`
- **Purpose**:
  - Consumes events from Kafka queues
  - Processes outbound synchronization
  - Updates external systems (Stripe)
  - Handles retries and error cases

## Bidirectional Sync Workflow

### 1. Outbound Sync (Internal → External)

The outbound sync process handles changes originating in our system that need to be propagated to external systems (e.g., Stripe).

#### Flow:
1. **Change Detection**
   ```mermaid
   sequenceDiagram
       Client->>API: Create/Update/Delete Customer
       API->>Database: Save Changes
       API->>Kafka: Publish to sync.outbound
       Worker->>Kafka: Consume Event
       Worker->>Stripe: Sync Changes
       Worker->>Database: Update Status
   ```

2. **Event Processing**
   - OutboundSyncWorker consumes from sync.outbound topic
   - Verifies external mapping existence
   - Performs corresponding action in external system:
     - Create: New customer in external system
     - Update: Modify existing customer
     - Delete: Remove customer
   - Updates sync event status

3. **State Management**
   - Maintains external mappings
   - Tracks sync event progress
   - Handles transaction boundaries
   - Ensures idempotency

### 2. Inbound Sync (External → Internal)

The inbound sync process handles changes from external systems that need to be reflected internally.

#### Flow:
1. **Event Reception**
   ```mermaid
   sequenceDiagram
       Stripe->>API: Webhook Event
       API->>Kafka: Publish to sync.inbound
       Worker->>Kafka: Consume Event
       Worker->>Database: Process Changes
       Worker->>Database: Update Mapping/Status
   ```

2. **Event Processing**
   - InboundSyncWorker consumes from sync.inbound topic
   - Processes based on event type:
     - customer.created: New customer + mapping
     - customer.updated: Update existing customer
     - customer.deleted: Remove customer + mapping
   - Updates sync event status

3. **Data Consistency**
   - Transactional processing
   - Mapping table synchronization
   - Full event history
   - Duplicate detection

### Error Handling & Recovery

1. **Worker Resilience**
   - Automatic Kafka reconnection
   - Configurable retry policies
   - Dead letter queue for failures
   - Exponential backoff

2. **Data Validation**
   - Schema validation
   - Business rule checks
   - External API error handling
   - Signature verification (webhooks)

3. **Monitoring & Recovery**
   - Event processing metrics
   - Error rate tracking
   - Queue depth monitoring
   - Manual recovery tools

## Monitoring & Debugging

1. **Logging**
   - JSON formatted logs
   - Configurable log levels
   - Container-specific logging

2. **Health Checks**
   - Database connectivity
   - Kafka broker status
   - Worker process health

3. **Event Tracking**
   - Sync event status monitoring
   - Error tracking and alerting
   - Performance metrics

## Adding New Integrations

To add a new integration (e.g., Salesforce):

1. Create new integration class extending `BaseIntegration`
2. Add webhook endpoint for the new system
3. Update external mapping table with new system
4. Configure new system credentials
5. Create system-specific transformers
6. Add new event types and handlers

## Future Extensions

The system is designed to support:

1. **Additional Catalogs**
   - Invoice management
   - Product catalog
   - Subscription management

2. **Enhanced Features**
   - Bulk synchronization
   - Data validation rules
   - Custom field mapping
   - Webhooks for internal changes

3. **Scaling Considerations**
   - Multiple worker instances
   - Kafka partitioning
   - Database sharding
