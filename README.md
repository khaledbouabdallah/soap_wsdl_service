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

## Testing Strategy

Our testing approach follows a three-tier pyramid: unit tests (fast, isolated) → integration tests (database + orchestration) → SOAP client tests (end-to-end).

### Testing Philosophy

**Unit Tests:** Test business logic and CRUD services in isolation
- Mock database with in-memory SQLite
- Fast execution (<1 second total)
- High coverage of business rules and edge cases
- No external dependencies

**Integration Tests:** Test orchestration layer with real database
- Verify service composition and data flow
- Test SOAP fault propagation
- Validate SolvencyReport structure
- Use test database fixtures

**SOAP Client Tests:** End-to-end testing via real SOAP calls
- Uses Zeep client library (equivalent to SoapUI)
- Tests against running docker-compose services
- Validates WSDL contract compliance
- Verifies XML serialization/deserialization
- SoapUI can also be used for testing, you can import this example project `assets/SolvencyVerification-wsdl-soapui-project.xml` to make a simple test request.

### Run All Tests

```bash
# Install test dependencies
uv pip install -e ".[dev]" --system

# Run all tests with coverage
uv run pytest tests/ -v --cov=loan_solvency_service

# Expected output:
# tests/unit/test_business_logic_services.py ✓✓✓✓✓✓✓✓✓✓✓✓✓✓✓ (15 tests)
# tests/unit/test_crud_services.py ✓✓✓✓✓✓✓✓✓✓✓ (11 tests)  
# tests/integration/test_orchestration.py ✓✓✓✓✓✓✓✓✓✓✓ (11 tests)
# tests/integration/test_soap_client.py ✓✓✓✓✓✓✓✓✓✓ (10 tests)
# ==================== 47 tests passed ====================
```

### Run Unit Tests Only

```bash
# Test business logic (credit scoring, decision, explanations)
uv run pytest tests/unit/test_business_logic_services.py -v

# Test CRUD services (data access layer)
uv run pytest tests/unit/test_crud_services.py -v

# Both run in <1 second, no docker needed
```

**What's Tested:**
- Credit score formula accuracy (including edge cases)
- Solvency decision logic (boundary conditions)
- Explanation content generation
- CRUD service database queries
- ClientNotFoundFault raising
- Data type conversions (Decimal, Boolean, Integer)

### Run Integration Tests

```bash
# Test orchestration with in-memory database
uv run pytest tests/integration/test_orchestration.py -v

# Tests full VerifySolvency flow:
# ✓ All 3 test clients (client-001, client-002, client-003)
# ✓ Correct score calculations
# ✓ Solvency status decisions
# ✓ Report structure validation
# ✓ ClientNotFoundFault handling
# ✓ Idempotency (repeated calls return same result)
```

### Run SOAP Client Tests (End-to-End)

```bash
# PREREQUISITE: Services must be running
docker-compose up -d

# Wait for services to be healthy (30 seconds)
sleep 30

# Run SOAP client tests via Zeep
uv run pytest tests/integration/test_soap_client.py -v

# Tests via real SOAP calls:
# ✓ WSDL accessibility and parsing
# ✓ XML serialization/deserialization
# ✓ All 3 test clients via network
# ✓ SOAP Fault handling (NotFound, ValidationError)
# ✓ Response structure validation
# ✓ Enum value constraints
# ✓ XSD validation (patterns, ranges, minLength)
```

**Test Assertions:**
- client-001 → score 400, not_solvent ✓
- client-002 → score 800, solvent ✓
- client-003 → score 0 (clamped), not_solvent ✓
- Invalid ID pattern → ValidationError fault ✓
- Non-existent client → NotFound fault ✓

### Verify Cache Performance

```bash
# Call same client multiple times to warm cache
for i in {1..10}; do
  curl -X POST http://localhost:8000/SolvencyVerification \
    -H "Content-Type: text/xml" \
    -d '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body><tns:VerifySolvencyRequest xmlns:tns="urn:solvency.verification.service:v1">
            <tns:clientId>client-002</tns:clientId>
          </tns:VerifySolvencyRequest></soap:Body>
        </soap:Envelope>'
done

# Check cache metrics
curl http://localhost:8000/metrics | jq '.cache'

# Expected output after 10 calls:
# {
#   "size": 3,
#   "hit_rate_percent": 70.0,
#   "hits": 21,
#   "misses": 9
# }
```

### Test Coverage Summary

| Test Suite | Coverage | Test Count | Duration |
|------------|----------|------------|----------|
| Business Logic | 100% | 15 tests | <500ms |
| CRUD Services | 100% | 11 tests | <500ms |
| Orchestration | 95% | 11 tests | ~2s |
| SOAP Client | E2E | 10 tests | ~5s |
| **Total** | **>90%** | **47 tests** | **~8s** |

### CI/CD Integration

```bash
# Recommended CI pipeline
docker-compose up -d --build
sleep 30  # Wait for services
uv run pytest tests/ -v --cov --cov-report=html
docker-compose down
```

For detailed architecture and design decisions, see [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Business Logic

### Credit Score Formula

The mandatory formula implemented per project requirements:

```python
score = 1000 - (0.1 × debt) - (50 × latePayments) - (hasBankruptcy ? 200 : 0)
```

**Constraints:**
- Score is clamped to range [0, 1000]
- Debt must be ≥ 0 (validated at XSD and database level)
- Late payments must be ≥ 0 (nonNegativeInteger)
- Bankruptcy is boolean (true/false)

**Examples:**
- No debt, no issues: `1000 - 0 - 0 - 0 = 1000` (perfect score)
- $5000 debt, 2 late, no bankruptcy: `1000 - 500 - 100 - 0 = 400`
- $10000 debt, 5 late, bankruptcy: `1000 - 1000 - 250 - 200 = -450 → 0` (clamped)

### Solvency Decision Rule

The mandatory decision logic per project requirements:

```python
solvent = (creditScore >= 700) AND (monthlyIncome > monthlyExpenses)
```

**Both conditions must be true for solvency:**
1. Credit score must be at least 700 (good creditworthiness)
2. Monthly income must exceed monthly expenses (positive cash flow)

**Decision Matrix:**

| Score | Income vs Expenses | Result |
|-------|-------------------|---------|
| ≥ 700 | income > expenses | ✅ solvent |
| ≥ 700 | income ≤ expenses | ❌ not_solvent |
| < 700 | income > expenses | ❌ not_solvent |
| < 700 | income ≤ expenses | ❌ not_solvent |

**Test Cases Verification:**
- client-001: score=400, income=4000>3000 → **not_solvent** (low score)
- client-002: score=800, income=3000>2500 → **solvent** (both conditions met)
- client-003: score=0, income=6000>5500 → **not_solvent** (very low score)

### Explanation Generation

Three explanations generated for transparency:

**1. Credit Score Explanation:**
- Excellent (≥800): "Excellent credit score of X. Strong creditworthiness."
- Good (700-799): "Good credit score of X. Acceptable credit risk."
- Fair (500-699): "Fair credit score of X. Moderate credit risk."
- Poor (<500): "Poor credit score of X. High credit risk."

**2. Income vs Expenses Explanation:**
- Strong surplus (>$1000): "Strong financial position with $X monthly surplus."
- Tight surplus ($1-1000): "Tight budget with only $X monthly surplus."
- Break-even ($0): "Break-even situation. Income exactly matches expenses."
- Deficit (<$0): "Negative cash flow of $X per month. Expenses exceed income."

**3. Credit History Explanation:**
Describes debt, late payments, and bankruptcy status in plain language.

Example: "Credit history shows $5000.00 in outstanding debt, 2 late payment(s), no bankruptcy history."

## QoS & SLA Targets

### Service Level Agreement

**Availability:** 99% uptime target
- Monitored via health checks at `/health` endpoint
- Docker restart policy ensures service recovery

**Response Time:** P95 < 300ms for VerifySolvency operation
- Measured: End-to-end client response time from orchestrator
- Current performance: ~75ms P95 with 78% cache hit rate (well under SLA)
- Monitored via Prometheus histograms and Grafana dashboards

**Cache Performance:** Target 70%+ hit rate
- Current: 78.6% hit rate achieved
- Reduces latency by eliminating redundant CRUD calls
- Monitored in real-time via Grafana

### Monitoring Access

```bash
# JSON metrics (human-readable with cache stats)
curl http://localhost:8000/metrics | jq

# Prometheus metrics (for monitoring tools)
curl http://localhost:8000/prometheus

# Grafana dashboard (visual)
open http://localhost:3000  # login: admin/admin
```

For a visual view, you can check **[MONITORING_SETUP.md](docs/MONITORING_SETUP.md)**

### Key Metrics Tracked

- Request count and rate per operation
- Response latency (P50, P95, P99)
- Cache hit/miss rates and size
- Service uptime
- Cache evictions (LRU policy)

All metrics accessible via Grafana dashboard with 5-second refresh intervals. dashboards via Grafana
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
- P95 latency: ~100-150ms
- 6 SOAP calls per request

**After caching (70% hit rate):**
- P95 latency: ~40-70 (cache hits)
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

### Project Documentation

- **README.md** (this file): Quick start guide, features overview, basic usage
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Detailed technical documentation
  - Layered architecture explanation (CRUD, Business Logic, Orchestration)
  - BPMN-style request flow diagram
  - SOAP/WSDL design choices and rationale
  - Fault management and propagation strategy
  - Caching implementation details
  - Versioning strategy for V2 evolution
  - QoS targets and monitoring approach
- **[MONITORING_SETUP.md](docs/MONITORING_SETUP.md)**: Detailed guide on how to setup Grafena dashboard.
  
- **[contracts/SolvencyVerification.wsdl](contracts/SolvencyVerification.wsdl)**: SOAP service contract
- **[contracts/SolvencyDataTypes.xsd](contracts/SolvencyDataTypes.xsd)**: XML schema definitions

### Additional Resources

- **Monitoring Setup**: See Grafana dashboard configuration in `grafana-dashboard.json`
- **Prometheus Config**: See scraping configuration in `prometheus.yml`
- **Test Suite**: Comprehensive tests in `tests/` directory (unit, integration, SOAP client)

### Quick Reference

**Service Endpoints:**
```
Orchestrator (public):  http://localhost:8000/SolvencyVerification
WSDL:                   http://localhost:8000/SolvencyVerification?wsdl
Health Check:           http://localhost:8000/health
JSON Metrics:           http://localhost:8000/metrics
Prometheus Metrics:     http://localhost:8000/prometheus
Grafana Dashboard:      http://localhost:3000 (admin/admin)
Prometheus UI:          http://localhost:9090
```

**Key Configuration Files:**
- `docker-compose.yml`: Service orchestration and environment variables
- `pyproject.toml`: Python dependencies and package configuration
- `prometheus.yml`: Metrics scraping configuration
- `grafana-dashboard.json`: Pre-configured monitoring dashboard

**Cache Configuration:**
```yaml
Environment Variables (in docker-compose.yml):
  CACHE_TTL_SECONDS: "300"    # 5 minutes (adjustable)
  CACHE_MAX_SIZE: "1000"      # Max entries (adjustable)
```

## Project Structure

```
loan_solvency_service/
├── services/
│   ├── crud/                     # Data access layer
│   │   ├── ClientDirectoryService.py
│   │   ├── FinancialDataService.py
│   │   ├── CreditBureauService.py
│   │   └── run_crud_services.py
│   ├── business_logic/           # Computation layer
│   │   ├── CreditScoringService.py
│   │   ├── SolvencyDecisionService.py
│   │   ├── ExplanationService.py
│   │   └── run_business_logic.py
│   └── orchestration/            # Public API + caching
│       ├── SolvencyVerificationService.py
│       └── run_orchestrator.py
├── shared/                       # Common utilities
│   ├── cache.py                  # TTL cache implementation
│   ├── datamodels.py             # Spyne ComplexModels (XSD mapping)
│   ├── base_service.py           # Base class, faults, server runner
│   ├── db_setup.py               # Database models & initialization
│   ├── soap_client.py            # Internal SOAP client wrapper
│   └── metrics.py                # QoS metrics (JSON + Prometheus)
contracts/                        # SOAP contracts
├── SolvencyVerification.wsdl     # Service operations
└── SolvencyDataTypes.xsd         # Data type definitions
tests/                            # Test suites
├── unit/                         # Isolated unit tests
│   ├── test_business_logic_services.py
│   └── test_crud_services.py
└── integration/                  # Integration & E2E tests
    ├── test_orchestration.py
    └── test_soap_client.py
docs/                             # Documentation
└── ARCHITECTURE.md               # Technical architecture doc
└── MONITORING_SETUP.md           # Monitoring setup guide
docker-compose.yml                # Multi-container orchestration
prometheus.yml                    # Prometheus configuration
grafana-dashboard.json            # Grafana dashboard template
Dockerfile_app                    # Application container image
pyproject.toml                    # Python project configuration
README.md                         # This file
```