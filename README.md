# Solvency Verification Service - SOAP/WSDL Implementation

A microservices-based loan solvency verification system using SOAP/WSDL, implementing SOA principles with separate CRUD, business logic, and orchestration layers.

## Architecture Overview

- **Orchestration Service**: Public-facing SOAP endpoint for solvency verification
- **CRUD Services**: Internal services for client data access (Identity, Financials, Credit History)
- **Business Logic Services**: Internal computation services (Credit Scoring, Solvency Decision, Explanations)
- **Database**: PostgreSQL for client data storage

All services communicate via SOAP. The orchestrator composes results from CRUD and business services.

## Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development/testing)
- uv (for dependency management)

## Quick Start

### 1. Start Services

```bash
# Build and start all services
docker-compose up --build

# Services will be available at:
# - Orchestrator (public): http://localhost:8000/SolvencyVerification
# - CRUD (internal): http://crud:8000/CRUDAccess
# - Business (internal): http://business:8000/BusinessLogic
```

### 2. Initialize Database

```bash
# Run once to create tables and insert test data
uv run python loan_solvency_service/shared/db_setup.py
```

### 3. Access WSDL

```
http://localhost:8000/SolvencyVerification?wsdl
```

### 4. Check Service Health

```bash
# Health check
curl http://localhost:8000/health

# Metrics (QoS monitoring)
curl http://localhost:8000/metrics
```

## Test Data

Three clients are pre-loaded:

| Client ID   | Name        | Expected Result |
|-------------|-------------|-----------------|
| client-001  | John Doe    | not_solvent (score: 400) |
| client-002  | Alice Smith | solvent (score: 800) |
| client-003  | Bob Johnson | not_solvent (score: 0) |

## Example SOAP Request

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="urn:solvency.verification.service:v1">
  <soap:Body>
    <tns:VerifySolvencyRequest>
      <tns:clientId>client-002</tns:clientId>
    </tns:VerifySolvencyRequest>
  </soap:Body>
</soap:Envelope>
```

## Example SOAP Response

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <tns:VerifySolvencyResponse xmlns:tns="urn:solvency.verification.service:v1">
      <tns:SolvencyReport>
        <tns:clientIdentity>
          <tns:name>Alice Smith</tns:name>
          <tns:address>456 Elm St</tns:address>
        </tns:clientIdentity>
        <tns:financials>
          <tns:monthlyIncome>3000.00</tns:monthlyIncome>
          <tns:monthlyExpenses>2500.00</tns:monthlyExpenses>
        </tns:financials>
        <tns:creditHistory>
          <tns:debt>2000.00</tns:debt>
          <tns:latePayments>0</tns:latePayments>
          <tns:hasBankruptcy>false</tns:hasBankruptcy>
        </tns:creditHistory>
        <tns:creditScore>800</tns:creditScore>
        <tns:solvencyStatus>solvent</tns:solvencyStatus>
        <tns:explanations>
          <tns:creditScoreExplanation>Excellent credit score of 800...</tns:creditScoreExplanation>
          <tns:incomeVsExpensesExplanation>Strong financial position...</tns:incomeVsExpensesExplanation>
          <tns:creditHistoryExplanation>Credit history shows...</tns:creditHistoryExplanation>
        </tns:explanations>
      </tns:SolvencyReport>
    </tns:VerifySolvencyResponse>
  </soap:Body>
</soap:Envelope>
```

## Testing

### Run Unit Tests

```bash
# Test business logic
uv run pytest tests/unit/test_business_logic_services.py -v

# Test CRUD services
uv run pytest tests/unit/test_crud_services.py -v

# Test orchestration
uv run pytest tests/integration/test_orchestration.py -v
```

### Run Integration Tests (SOAP Client)

```bash
# Requires docker-compose services running
docker-compose up -d
uv run pytest tests/integration/test_soap_client.py -v
```

## Business Logic

### Credit Score Formula

```
score = 1000 - (0.1 × debt) - (50 × latePayments) - (hasBankruptcy ? 200 : 0)
```

Clamped to [0, 1000]

### Solvency Decision Rule

```
solvent = (creditScore >= 700) AND (monthlyIncome > monthlyExpenses)
```

## QoS & SLA Targets

- **Availability**: 99% uptime target
- **Latency**: P95 < 300ms for VerifySolvency operation
- **Monitoring**: Metrics exposed at `/metrics` endpoint with:
  - Call counts per operation
  - Average, min, max, P95 latency
  - Service uptime

## Logging & Tracing

All requests are tracked with:
- **Correlation ID**: UUID generated at entry point, propagated through all service calls
- **Latency Tracking**: Every operation logs execution time
- **Format**: `[correlation-id][client-id]: message (XXms)`

Example log:
```
2025-10-19 10:30:45 - [a1b2c3d4-...][client-001]: Starting solvency verification
2025-10-19 10:30:45 - [a1b2c3d4-...][client-001]: Identity retrieved (12.34ms)
```

## Error Handling

### SOAP Faults

- **Client.NotFound**: Client ID doesn't exist in database
- **Client.ValidationError**: Invalid client ID format (must match pattern: `client-\d{3}`)

Both faults propagate from internal services to the client.

## Technology Stack

- **SOAP Framework**: Spyne 2.14+
- **SOAP Client**: Zeep 4.0+
- **Web Server**: Twisted 22.8+
- **Database**: PostgreSQL 18 + SQLAlchemy 2.0
- **Container**: Docker with docker-compose

## Project Structure

```
loan_solvency_service/
├── services/
│   ├── crud/              # Client data access services
│   ├── business_logic/    # Computation services
│   └── orchestration/     # Main public endpoint
├── shared/
│   ├── datamodels.py      # Spyne ComplexModels (maps to XSD)
│   ├── base_service.py    # Base class, faults, metrics
│   ├── db_setup.py        # Database models & setup
│   ├── soap_client.py     # Internal SOAP client wrapper
│   └── metrics.py         # QoS metrics collection
contracts/
├── SolvencyVerification.wsdl
└── SolvencyDataTypes.xsd
tests/
├── unit/
└── integration/
```

## Versioning Strategy

Current version: **v1** (namespace: `urn:solvency.verification.service:v1`)

**For V2**:
- Create new namespace: `urn:solvency.verification.service:v2`
- Use XSD extension/restriction for backward compatibility
- Add optional fields without breaking existing clients
- Run V1 and V2 endpoints in parallel during transition

## Limitations & Future Improvements

### Current Limitations
- In-memory metrics (reset on restart)
- No authentication/authorization (WS-Security)
- No message-level encryption
- Basic error messages

### Potential Improvements
- **Security**: Implement WS-Security for authentication and encryption
- **Persistence**: Store metrics in time-series database (Prometheus, InfluxDB)
- **Monitoring**: Add Grafana dashboards for real-time monitoring
- **Caching**: Cache CRUD results in orchestrator for repeated calls
- **Load Balancing**: Add multiple instances with load balancer
- **Circuit Breaker**: Implement fault tolerance patterns
- **Async Processing**: Queue-based processing for high volume

## License

MIT