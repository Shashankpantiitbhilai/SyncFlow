# Integration Plans

## Salesforce Customer Catalog Integration

### 1. Architecture Extension
The current architecture is designed with extensibility in mind, using a base integration interface that can be implemented for different external systems.

```python
class BaseIntegration:
    async def create_customer(self, data: dict) -> str:
        """Create customer in external system"""
        pass
    
    async def update_customer(self, external_id: str, data: dict) -> bool:
        """Update customer in external system"""
        pass
    
    async def delete_customer(self, external_id: str) -> bool:
        """Delete customer in external system"""
        pass
```

### 2. Implementation Steps for Salesforce

1. **Salesforce Integration Client**
   ```python
   # src/integrations/salesforce/client.py
   class SalesforceIntegration(BaseIntegration):
       def __init__(self):
           self.client = Salesforce(
               username=settings.SF_USERNAME,
               password=settings.SF_PASSWORD,
               security_token=settings.SF_TOKEN
           )
       
       async def create_customer(self, data: dict) -> str:
           # Transform internal customer data to Salesforce Contact/Account format
           sf_data = self._transform_to_salesforce_format(data)
           # Create record in Salesforce
           return self.client.Contact.create(sf_data)
   ```

2. **Data Mapping Layer**
   - Create Salesforce-specific field mappings
   - Handle Salesforce's specific data types and validations
   - Map between internal customer model and Salesforce Contact/Account objects

3. **Webhook Configuration**
   - Implement Salesforce outbound message handling
   - Add Salesforce-specific webhook endpoint
   - Handle Salesforce's authentication mechanism

4. **Database Changes**
   ```sql
   -- Add Salesforce-specific columns to external_mappings
   ALTER TABLE external_mappings
   ADD COLUMN sf_account_id VARCHAR,
   ADD COLUMN sf_contact_id VARCHAR;
   ```

5. **Event Processing**
   - Add Salesforce event types to event processor
   - Handle Salesforce-specific error cases
   - Implement retry logic for Salesforce API limits

### 3. Configuration Changes
```python
# src/core/config.py
class Settings:
    # Existing settings...
    
    # Salesforce settings
    SF_USERNAME: str
    SF_PASSWORD: str
    SF_TOKEN: str
    SF_INSTANCE_URL: str
```

## Extending to Other Catalogs (e.g., Invoice)

### 1. Base Catalog Interface
```python
class BaseCatalog:
    def __init__(self):
        self.integrations = []
    
    async def register_integration(self, integration: BaseIntegration):
        self.integrations.append(integration)
    
    async def sync_create(self, data: dict):
        """Sync creation across all registered integrations"""
        pass
    
    async def sync_update(self, data: dict):
        """Sync updates across all registered integrations"""
        pass
```

### 2. Implementation Structure

1. **Models Layer**
   ```python
   # src/models/invoice.py
   class Invoice(Base):
       __tablename__ = "invoices"
       id = Column(Integer, primary_key=True)
       customer_id = Column(Integer, ForeignKey("customers.id"))
       amount = Column(Numeric)
       status = Column(String)
       # ... other fields
   
   # src/models/external_invoice_mapping.py
   class ExternalInvoiceMapping(Base):
       __tablename__ = "external_invoice_mappings"
       id = Column(Integer, primary_key=True)
       internal_invoice_id = Column(Integer, ForeignKey("invoices.id"))
       external_system = Column(String)  # "stripe", "salesforce"
       external_id = Column(String)
   ```

2. **Event System Extension**
   ```python
   # src/core/topics.py
   class KafkaTopics:
       # Existing topics...
       INVOICE_SYNC_OUTBOUND = "invoice.sync.outbound"
       INVOICE_SYNC_INBOUND = "invoice.sync.inbound"
   ```

3. **Integration Interface Extension**
   ```python
   class InvoiceIntegration(BaseIntegration):
       async def create_invoice(self, data: dict) -> str:
           pass
       
       async def update_invoice(self, external_id: str, data: dict) -> bool:
           pass
       
       async def delete_invoice(self, external_id: str) -> bool:
           pass
   ```

4. **Sync Workers**
   ```python
   class InvoiceSyncWorker(BaseWorker):
       def __init__(self):
           super().__init__("invoice-sync", "zenskar-invoice-sync")
           self.stripe = StripeInvoiceIntegration()
           self.salesforce = SalesforceInvoiceIntegration()
   ```

### 3. Reusable Components

1. **Base Mapping System**
   - Generic external mapping table structure
   - Reusable sync event logging
   - Common error handling patterns

2. **Event Processing Pipeline**
   - Common message format for all catalogs
   - Shared retry logic
   - Unified error handling

3. **Integration Base Classes**
   - Common authentication handling
   - Rate limiting
   - Error recovery

### 4. Implementation Process for New Catalogs

1. Create catalog-specific models
2. Implement catalog integration interface
3. Create catalog-specific workers
4. Add Kafka topics for the catalog
5. Implement external system mappings
6. Add webhook endpoints if needed
7. Configure error handling and retries

This modular approach allows easy addition of:
- New external systems to existing catalogs
- New catalogs with multiple integrations
- Different sync strategies per catalog/integration
