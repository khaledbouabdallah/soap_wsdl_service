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

## Troubleshooting

### Prometheus not scraping services

1. Check Prometheus targets: http://localhost:9090/targets
2. All targets should show "UP" status
3. If DOWN, check:
   - Services are running: `docker-compose ps`
   - Network connectivity: `docker exec prometheus ping orchestrator`

### Grafana not showing data

1. Verify Prometheus data source is configured correctly
2. Check query syntax in panel settings
3. Ensure time range is appropriate (last 15 minutes)

### No metrics showing

1. Generate some test traffic (see "Testing the Monitoring" section)
2. Check if services are exposing metrics:
   ```bash
   curl http://localhost:8000/prometheus
   ```
3. Check Prometheus scrape config:
   ```bash
   docker exec prometheus cat /etc/prometheus/prometheus.yml
   ```

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

## SLA Monitoring

### Target SLA: P95 Latency < 300ms

Create an alert in Grafana:

1. Edit the P95 Latency panel
2. Go to **Alert** tab
3. Create new alert rule:
   - Condition: `WHEN avg() OF query(A, 5m, now) IS ABOVE 0.3`
   - Alert name: "High Latency - SLA Violation"
   - Message: "P95 latency exceeded 300ms target"

### Target SLA: 99% Availability

Create uptime alert:

1. Create new panel with query:
   ```promql
   avg_over_time(up{job=~"solvency.*"}[5m]) < 0.99
   ```
2. Add alert when condition triggers
3. Message: "Service availability below 99%"

## Advanced: Custom Dashboard Template

Create a more sophisticated dashboard with these panels:

### Row 1: Overview
- Total Requests (Stat)
- Success Rate (Gauge)
- Average Latency (Stat)
- P95 Latency (Stat with threshold alert)

### Row 2: Request Patterns
- Request Rate by Service (Graph)
- Request Rate by Operation (Graph)
- Request Distribution (Pie Chart)

### Row 3: Performance
- Latency Heatmap (Heatmap)
- Latency by Operation (Graph)
- Slowest Operations (Table)

### Row 4: Service Health
- Service Uptime (Stat)
- Error Rate (Graph)
- Service Status (Stat with health indicators)

## Integration with CI/CD

You can query Prometheus programmatically:

```bash
# Check if P95 latency is within SLA
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(soap_request_duration_seconds_bucket[5m]))' \
  | jq '.data.result[0].value[1]'

# Fail build if latency > 300ms
LATENCY=$(curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(soap_request_duration_seconds_bucket[5m]))' \
  | jq -r '.data.result[0].value[1]')

if (( $(echo "$LATENCY > 0.3" | bc -l) )); then
  echo "SLA violation: P95 latency ${LATENCY}s exceeds 300ms"
  exit 1
fi
```

## Useful Resources

- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- PromQL Tutorial: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Grafana Dashboard Gallery: https://grafana.com/grafana/dashboards/