# Solvency Verification Service - SOAP/WSDL Implementation

A microservices-based loan solvency verification system using SOAP/WSDL, implementing SOA principles with separate CRUD, business logic, and orchestration layers. Includes production-grade monitoring with Prometheus and Grafana, plus intelligent caching for performance optimization.

## Architecture Overview

- **Orchestration Service**: Public-facing SOAP endpoint with TTL-based caching layer
- **CRUD Services**: Internal services for client data access (Identity, Financials, Credit History)
- **Business Logic Services**: Internal computation services (Credit Scoring, Solvency Decision, Explanations)
- **Database**: PostgreSQL for client data storage
- **Monitoring**: Prometheus + Grafana for metrics collection and visualization
- **Caching**: In-memory TTL cache for CRUD operations with LRU eviction

All services communicate via SOAP. The orchestrator composes results from CRUD and business services. Each request is tracked with correlation IDs and latency metrics. CRUD responses are cached at the orchestrator level to reduce latency and SOAP overhead.

## Key Features

✅ **Performance Optimization**: Intelligent caching reduces P95 latency by 40-60% on cache hits  
✅ **SOA Architecture**: Clear separation of concerns across services  
✅ **Comprehensive Monitoring**: Real-time metrics, dashboards, and SLA tracking  
✅ **Request Tracing**: End-to-end correlation IDs for debugging  
✅ **SOAP/WSDL Compliance**: Document/literal style with XSD validation  

## Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development/testing)
- uv (for dependency management)

## Quick Start

### 1. Start Services

```bash
# Build and start all services
docker-compose up --build

# Services available at:
# - Orchestrator (public): http://localhost:8000/SolvencyVerification
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
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

### 4. Monitor Service Health & Metrics

```bash
# Health check
curl http://localhost:8000/health

# JSON Metrics (includes cache stats)
curl http://localhost:8000/metrics

# Prometheus Metrics
curl http://localhost:8000/prometheus
```

## Cache Configuration

The orchestrator uses an in-memory TTL cache for CRUD operations. Configure via environment variables:

```yaml
# In docker-compose.yml
environment:
  CACHE_TTL_SECONDS: "300"    # Time-to-live (default: 5 minutes)
  CACHE_MAX_SIZE: "1000"      # Max entries (default: 1000)
```

**What's cached:**
- Client Identity lookups
- Financial data queries  
- Credit history retrievals

**What's NOT cached:**
- Business logic computations (fast, deterministic)
- Final solvency reports (always fresh)

**Cache metrics available:**
- Hit rate percentage
- Cache size and capacity
- Evictions count
- Response time savings

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

### Verify Cache Performance

```bash
# Call same client multiple times
curl http://localhost:8000/metrics | grep cache

# Expected output shows improving hit rate:
# "cache": {
#   "hit_rate_percent": 66.67,
#   "hits": 6,
#   "misses": 3
# }
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
- **Latency**: P95 < 300ms for VerifySolvency (cache helps achieve this)
- **Cache Hit Rate**: Target 70%+ in production scenarios
- **Monitoring**: 
  - Real-time metrics via Prometheus (5s scrape interval)
  - Visual dashboards via Grafana
  - Cache performance tracking

### Key Metrics Tracked
- Request count per operation
- Request latency (avg, min, max, P95)
- Cache hit/miss rates
- Cache size and evictions
- Service uptime
- Time saved by caching

## Logging & Tracing

All requests tracked with:
- **Correlation ID**: UUID propagated through all service calls
- **Cache Events**: Explicit logging of hits/misses
- **Latency Tracking**: Every operation logs execution time
- **Format**: `[correlation-id][client-id]: message (XXms)`

Example log with cache:
```
2025-10-19 10:30:45 - [a1b2c3d4-...][client-001]: Starting solvency verification
2025-10-19 10:30:45 - [a1b2c3d4-...][client-001]: Cache MISS for identity:client-001
2025-10-19 10:30:45 - [a1b2c3d4-...][client-001]: Identity retrieved (12.34ms)
2025-10-19 10:30:50 - [a1b2c3d4-...][client-001]: Cache HIT for identity:client-001
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
- **Monitoring**: Prometheus + Grafana
- **Metrics**: prometheus-client
- **Caching**: Custom TTL cache with LRU eviction
- **Container**: Docker with docker-compose

## Monitoring & Observability

### Architecture
```
Services (Orchestrator + Cache, Business, CRUD)
    ↓ expose /prometheus endpoint
Prometheus (scrapes every 5s)
    ↓ stores time-series data
Grafana (visualizes)
    ↓ dashboards & alerts
```

### Accessing Monitoring Tools
- **Grafana Dashboard**: http://localhost:3000 (login: admin/admin)
- **Prometheus UI**: http://localhost:9090
- **Service Metrics**: http://localhost:8000/metrics (JSON with cache stats)

### Available Metrics
1. `soap_requests_total` - Total requests per operation
2. `soap_request_duration_seconds` - Request latency histogram
3. `soap_service_uptime_seconds` - Service uptime
4. `soap_cache_hits_total` - Cache hit counter
5. `soap_cache_misses_total` - Cache miss counter
6. `soap_cache_size` - Current cache entries
7. `soap_cache_evictions_total` - LRU evictions

## Project Structure

```
loan_solvency_service/
├── services/
│   ├── crud/              # Client data access services
│   ├── business_logic/    # Computation services
│   └── orchestration/     # Main endpoint + cache layer
├── shared/
│   ├── cache.py           # TTL cache implementation
│   ├── datamodels.py      # Spyne ComplexModels
│   ├── base_service.py    # Base class, faults, metrics
│   ├── db_setup.py        # Database models
│   ├── soap_client.py     # Internal SOAP client
│   └── metrics.py         # QoS metrics (JSON + Prometheus)
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
- Cache invalidation strategy for data model changes
- Run V1 and V2 endpoints in parallel

## Performance Impact

**Before caching:**
- P95 latency: ~200-250ms
- 6 SOAP calls per request

**After caching (70% hit rate):**
- P95 latency: ~80-120ms (cache hits)
- 3 business logic calls only (CRUD from cache)
- 40-60% latency reduction on cached requests

## Limitations & Future Improvements

### Current Limitations
- Cache not shared across orchestrator instances
- No authentication/authorization (WS-Security)
- Manual cache invalidation only (TTL-based)

### Potential Improvements
- **Distributed Cache**: Redis for multi-instance deployments
- **Cache Warming**: Pre-populate frequently accessed clients
- **Intelligent Invalidation**: Event-based cache updates
- **Security**: Implement WS-Security
- **Advanced Monitoring**: Distributed tracing, custom alerts

## Documentation

- **Main README**: This file (getting started, overview)
- **Detailed Report**: See separate 2-page architecture document
- **WSDL Contract**: [contracts/SolvencyVerification.wsdl](contracts/SolvencyVerification.wsdl)
- **XSD Types**: [contracts/SolvencyDataTypes.xsd](contracts/SolvencyDataTypes.xsd)

## License

MIT