import time
import threading
from collections import defaultdict
from typing import Dict, List, Optional

# Prometheus imports
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


class MetricsCollector:
    """
    Thread-safe metrics collection for QoS monitoring.
    Tracks call counts and latencies per operation.
    Supports both JSON export and Prometheus format.
    **ENHANCED: Now includes cache metrics tracking.**
    """

    def __init__(self, service_name="unknown"):
        self._lock = threading.Lock()
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._operation_latencies: Dict[str, List[float]] = defaultdict(list)
        self._start_time = time.time()
        self.service_name = service_name

        # Prometheus metrics
        self.prom_request_counter = Counter(
            "soap_requests_total",
            "Total number of SOAP requests",
            ["service", "operation"],
        )

        self.prom_request_latency = Histogram(
            "soap_request_duration_seconds",
            "SOAP request latency in seconds",
            ["service", "operation"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        self.prom_uptime = Gauge(
            "soap_service_uptime_seconds", "Service uptime in seconds", ["service"]
        )

        # Cache metrics
        self.prom_cache_hits = Counter(
            "soap_cache_hits_total", "Total number of cache hits", ["service"]
        )

        self.prom_cache_misses = Counter(
            "soap_cache_misses_total", "Total number of cache misses", ["service"]
        )

        self.prom_cache_size = Gauge(
            "soap_cache_size", "Current number of entries in cache", ["service"]
        )

        self.prom_cache_evictions = Counter(
            "soap_cache_evictions_total", "Total number of cache evictions", ["service"]
        )

        # **NEW: Track last values for delta calculation**
        self._last_cache_hits = 0
        self._last_cache_misses = 0
        self._last_cache_evictions = 0

    def record_call(self, operation_name: str, latency_ms: float):
        """
        Record a service call with its latency.

        :param operation_name: Name of the operation
        :param latency_ms: Latency in milliseconds
        """
        with self._lock:
            self._operation_counts[operation_name] += 1
            self._operation_latencies[operation_name].append(latency_ms)

        # Update Prometheus metrics
        self.prom_request_counter.labels(
            service=self.service_name, operation=operation_name
        ).inc()

        self.prom_request_latency.labels(
            service=self.service_name, operation=operation_name
        ).observe(
            latency_ms / 1000.0
        )  # Convert ms to seconds

    def update_cache_metrics(self, cache_stats: Dict):
        """
        Update cache-related metrics.

        :param cache_stats: Dictionary from TTLCache.get_stats()
        """
        # Update cache size gauge (Gauge uses .set())
        self.prom_cache_size.labels(service=self.service_name).set(cache_stats["size"])

        # **FIXED: Counters must be incremented, not set**
        # Calculate deltas since last update
        hits_delta = cache_stats["hits"] - self._last_cache_hits
        misses_delta = cache_stats["misses"] - self._last_cache_misses
        evictions_delta = cache_stats["evictions"] - self._last_cache_evictions

        # Increment counters by delta (Counter uses .inc())
        if hits_delta > 0:
            self.prom_cache_hits.labels(service=self.service_name).inc(hits_delta)
        if misses_delta > 0:
            self.prom_cache_misses.labels(service=self.service_name).inc(misses_delta)
        if evictions_delta > 0:
            self.prom_cache_evictions.labels(service=self.service_name).inc(
                evictions_delta
            )

        # Update last known values
        self._last_cache_hits = cache_stats["hits"]
        self._last_cache_misses = cache_stats["misses"]
        self._last_cache_evictions = cache_stats["evictions"]

    def get_metrics(self, cache_stats: Optional[Dict] = None) -> dict:
        """
        Get current metrics snapshot in JSON format.

        :param cache_stats: Optional cache statistics to include
        :return: Dictionary with metrics
        """
        with self._lock:
            uptime = time.time() - self._start_time

            # Update uptime gauge
            self.prom_uptime.labels(service=self.service_name).set(uptime)

            metrics = {"uptime_seconds": uptime, "operations": {}}

            # Include cache stats if provided
            if cache_stats:
                metrics["cache"] = cache_stats
                self.update_cache_metrics(cache_stats)

            for operation_name in self._operation_counts:
                latencies = self._operation_latencies[operation_name]
                count = self._operation_counts[operation_name]

                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    min_latency = min(latencies)
                    max_latency = max(latencies)

                    # Calculate p95 (95th percentile)
                    sorted_latencies = sorted(latencies)
                    p95_index = int(len(sorted_latencies) * 0.95)
                    p95_latency = (
                        sorted_latencies[p95_index]
                        if p95_index < len(sorted_latencies)
                        else max_latency
                    )
                else:
                    avg_latency = min_latency = max_latency = p95_latency = 0

                metrics["operations"][operation_name] = {
                    "call_count": count,
                    "avg_latency_ms": round(avg_latency, 2),
                    "min_latency_ms": round(min_latency, 2),
                    "max_latency_ms": round(max_latency, 2),
                    "p95_latency_ms": round(p95_latency, 2),
                }

            return metrics

    def get_prometheus_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format.

        :return: Prometheus metrics as bytes
        """
        # Update uptime before export
        uptime = time.time() - self._start_time
        self.prom_uptime.labels(service=self.service_name).set(uptime)

        return generate_latest()

    def get_summary(self, cache_stats: Optional[Dict] = None) -> str:
        """
        Get human-readable metrics summary.

        :param cache_stats: Optional cache statistics to include
        :return: Formatted string with metrics
        """
        metrics = self.get_metrics(cache_stats)
        uptime = metrics["uptime_seconds"]

        lines = [
            f"Service Uptime: {uptime:.2f}s",
            f"Total Operations: {len(metrics['operations'])}",
            "",
        ]

        # Add cache summary
        if "cache" in metrics:
            cache = metrics["cache"]
            lines.append("Cache Statistics:")
            lines.append(f"  Size: {cache['size']}/{cache['max_size']}")
            lines.append(f"  Hit Rate: {cache['hit_rate_percent']}%")
            lines.append(f"  Hits: {cache['hits']}, Misses: {cache['misses']}")
            lines.append(f"  Evictions: {cache['evictions']}")
            lines.append("")

        for op_name, op_metrics in metrics["operations"].items():
            lines.append(f"{op_name}:")
            lines.append(f"  Calls: {op_metrics['call_count']}")
            lines.append(f"  Avg Latency: {op_metrics['avg_latency_ms']}ms")
            lines.append(f"  P95 Latency: {op_metrics['p95_latency_ms']}ms")
            lines.append(
                f"  Min/Max: {op_metrics['min_latency_ms']}/{op_metrics['max_latency_ms']}ms"
            )
            lines.append("")

        return "\n".join(lines)


# Global metrics collector instance per service
_metrics_collector = None


def get_metrics_collector(service_name="unknown") -> MetricsCollector:
    """Get or create the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(service_name)
    return _metrics_collector


def get_prometheus_content_type():
    """Get Prometheus content type for HTTP response."""
    return CONTENT_TYPE_LATEST
