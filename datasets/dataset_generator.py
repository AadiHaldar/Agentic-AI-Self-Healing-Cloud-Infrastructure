import os
import pandas as pd
import numpy as np

def generate_datasets():
    """Generates synthetic baseline datasets matching cloud telemetry & IDS benchmarks."""
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    np.random.seed(42)

    # 1. Healthy Telemetry Dataset (1000 samples)
    cpu_healthy = np.random.normal(loc=0.25, scale=0.05, size=1000)
    mem_healthy = np.random.normal(loc=0.40, scale=0.08, size=1000)
    latency_healthy = np.random.normal(loc=45.0, scale=5.0, size=1000) # ms
    req_rate_healthy = np.random.normal(loc=120.0, scale=15.0, size=1000)

    df_healthy = pd.DataFrame({
        "cpu_usage": np.clip(cpu_healthy, 0.05, 0.50),
        "memory_usage": np.clip(mem_healthy, 0.10, 0.65),
        "latency_ms": np.clip(latency_healthy, 20.0, 80.0),
        "request_rate": np.clip(req_rate_healthy, 50.0, 200.0),
        "is_anomaly": 0
    })
    df_healthy.to_csv(os.path.join(os.path.dirname(__file__), "healthy_telemetry.csv"), index=False)

    # 2. Chaos Injected Anomalies Dataset (500 samples)
    cpu_anom = np.random.uniform(low=0.80, high=0.99, size=500)
    mem_anom = np.random.uniform(low=0.75, high=0.98, size=500)
    latency_anom = np.random.uniform(low=300.0, high=2500.0, size=500)
    req_rate_anom = np.random.uniform(low=500.0, high=3000.0, size=500)

    df_anom = pd.DataFrame({
        "cpu_usage": cpu_anom,
        "memory_usage": mem_anom,
        "latency_ms": latency_anom,
        "request_rate": req_rate_anom,
        "is_anomaly": 1
    })
    df_anom.to_csv(os.path.join(os.path.dirname(__file__), "chaos_anomalies.csv"), index=False)

    # 3. XGBoost IDS Traffic Dataset (1000 samples)
    # Features: packet_count, byte_rate, syn_flag_count, error_rate
    healthy_traffic = np.random.normal(loc=[100, 5000, 1, 0.01], scale=[10, 500, 0.5, 0.005], size=(700, 4))
    malicious_traffic = np.random.normal(loc=[5000, 250000, 500, 0.45], scale=[500, 25000, 50, 0.10], size=(300, 4))

    traffic_features = np.vstack([healthy_traffic, malicious_traffic])
    labels = np.array([0]*700 + [1]*300)

    df_ids = pd.DataFrame(traffic_features, columns=["packet_count", "byte_rate", "syn_flag_count", "error_rate"])
    df_ids["is_malicious"] = labels
    df_ids.to_csv(os.path.join(os.path.dirname(__file__), "ids_traffic.csv"), index=False)

    print("Successfully generated healthy_telemetry.csv, chaos_anomalies.csv, and ids_traffic.csv!")

if __name__ == "__main__":
    generate_datasets()
