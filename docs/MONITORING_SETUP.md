# Prometheus + Grafana Monitoring Setup

## Quick Start

### 1. Start all services

```bash
docker-compose up --build
```

Wait for all services to start (about 30 seconds).

### 2. Access the dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Service Metrics (JSON)**: http://localhost:8000/metrics
- **Service Metrics (Prometheus)**: http://localhost:8000/prometheus

### 3. Login to Grafana

```
Username: admin
Password: admin
```

(You'll be prompted to change the password on first login)

## Setup Grafana Dashboard

### Step 1: Add Prometheus Data Source

1. Go to **Configuration** → **Data Sources** (gear icon on left sidebar)
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL to: `http://prometheus:9090`
5. Click **Save & Test**

### Step 2: Import Dashboard

1. Click **+** icon on left sidebar → **Import**
2. Paste this dashboard JSON or create your own:

#### Quick Dashboard JSON

3. Click **Load** → **Import**
4. upload `grafana-dashboard.json` file

### Step 3: Create Custom Panels (Manual)

If you prefer to create panels manually:

#### Panel 1: Request Rate
- Query: `rate(soap_requests_total[5m])`
- Visualization: Graph
- Legend: `{{service}} - {{operation}}`

#### Panel 2: Average Latency
- Query: `rate(soap_request_duration_seconds_sum[5m]) / rate(soap_request_duration_seconds_count[5m])`
- Visualization: Graph
- Unit: seconds

#### Panel 3: P95 Latency
- Query: `histogram_quantile(0.95, rate(soap_request_duration_seconds_bucket[5m]))`
- Visualization: Graph
- Unit: seconds
- Alert: Set threshold at 0.3 (300ms target)

#### Panel 4: Total Requests by Operation
- Query: `soap_requests_total`
- Visualization: Bar Chart
- Group by: operation

#### Panel 5: Service Uptime
- Query: `soap_service_uptime_seconds`
- Visualization: Stat
- Unit: seconds

## Available Metrics

### Prometheus Metrics

All services expose these metrics at `/prometheus`:

1. **soap_requests_total**
   - Type: Counter
   - Labels: service, operation
   - Description: Total SOAP requests per operation

2. **soap_request_duration_seconds**
   - Type: Histogram
   - Labels: service, operation
   - Buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
   - Description: Request latency distribution

3. **soap_service_uptime_seconds**
   - Type: Gauge
   - Labels: service
   - Description: Service uptime in seconds

### JSON Metrics

For debugging, each service also exposes JSON metrics at `/metrics`:

```bash
# Orchestrator metrics
curl http://localhost:8000/metrics | jq

# Business service metrics (internal only, from within docker)
docker exec solvency_orchestrator curl http://business:8000/metrics | jq

# CRUD service metrics (internal only, from within docker)
docker exec solvency_orchestrator curl http://crud:8000/metrics | jq
```

## Example Queries in Prometheus

Access Prometheus at http://localhost:9090 and try these queries:

### 1. Total requests per service
```promql
sum by (service) (soap_requests_total)
```

### 2. Request rate (last 5 minutes)
```promql
rate(soap_requests_total[5m])
```

### 3. Average latency by operation
```promql
rate(soap_request_duration_seconds_sum[5m]) / rate(soap_request_duration_seconds_count[5m])
```

### 4. P95 latency (95th percentile)
```promql
histogram_quantile(0.95, rate(soap_request_duration_seconds_bucket[5m]))
```

### 5. Check if services are up
```promql
up{job=~"solvency.*"}
```

### 6. Requests slower than 300ms (SLA violation)
```promql
histogram_quantile(0.95, rate(soap_request_duration_seconds_bucket[5m])) > 0.3
```

## Testing the Monitoring

### Generate some traffic

```bash
# Using curl with SOAP
for i in {1..100}; do
  curl -X POST http://localhost:8000/SolvencyVerification \
    -H "Content-Type: text/xml" \
    -d '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="urn:solvency.verification.service:v1">
          <soap:Body>
            <tns:VerifySolvencyRequest>
              <tns:clientId>client-002</tns:clientId>
            </tns:VerifySolvencyRequest>
          </soap:Body>
        </soap:Envelope>'
  sleep 0.1
done
```

### Check metrics updated

1. Refresh Grafana dashboard
2. Check Prometheus targets: http://localhost:9090/targets
3. Query metrics directly: http://localhost:8000/prometheus

## Persistence

All data is persisted in Docker volumes:

- **prometheus_data**: Prometheus time-series data
- **grafana_data**: Grafana dashboards and settings
- **postgres_data**: Application database

Even if you restart containers, your metrics history and dashboards are preserved.

### Cleanup (if needed)

```bash
# Stop and remove containers
docker-compose down

# Remove all data (WARNING: deletes all metrics and dashboards)
docker-compose down -v
```

## Useful Resources

- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- PromQL Tutorial: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Grafana Dashboard Gallery: https://grafana.com/grafana/dashboards/