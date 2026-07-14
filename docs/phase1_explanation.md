# Phase 1: Foundation and Infrastructure

## Project Scaffolding
We created a clean, modular folder structure to keep the project organized:
* `infrastructure/k8s/app/`: Holds the code for the test application.
* `infrastructure/k8s/monitoring/`: Holds the code for collecting data (the "eyes" of our AI).
* `infrastructure/k8s/chaos-mesh/`: Holds the code for breaking the system on purpose.
* `infrastructure/terraform/azure/`: Holds the code to build our actual cloud servers later.
* `scripts/`: Holds automation scripts so you don't have to type commands manually.

## The Test Application: Google Online Boutique
We downloaded the official Kubernetes manifests for **Google's Online Boutique** and saved them to `infrastructure/k8s/app/online-boutique.yaml`.

* **What it is:** A highly realistic, 10-tier microservices application (it has a frontend, a checkout service, a redis cache, an email service, a payment gateway, etc.).
* **Why we used it:** To prove that our Agentic AI works, we can't just test it on a simple "Hello World" app. We need a complex web of interconnected services where a failure in one service (like the payment gateway) causes cascading failures. This makes it the perfect "guinea pig" for our self-healing AI to fix.

## The Monitoring Stack (The "Eyes" of the AI)
Inside the `setup_local.ps1` script, I wrote the commands to deploy a full monitoring stack to your cluster. 

* **Prometheus:** 
  * **What it is:** A time-series database that constantly scrapes metrics (CPU usage, RAM usage, network bandwidth, request latency) from every single pod in the cluster.
  * **Why we used it:** This is the primary data source for our Digital Twin. The Digital Twin cannot simulate the future without knowing exactly what the cluster looks like *right now*.
* **Grafana:**
  * **What it is:** A visualization dashboard.
  * **Why we used it:** While the AI reads raw numbers from Prometheus, humans need charts. Grafana will allow you to visually verify that the metrics the AI is looking at are correct.
* **Loki:**
  * **What it is:** A log aggregation system (similar to Splunk or ElasticSearch, but much more lightweight).
  * **Why we used it:** Metrics tell you *when* a server crashes, but logs tell you *why*. We use Loki so our LLM Agent can read the error logs to figure out exactly what broke before it attempts a fix.

## Fault Injection: Chaos Mesh
Also in the `setup_local.ps1` script, I included the installation for **Chaos Mesh**.

* **What it is:** A "Chaos Engineering" tool built specifically for Kubernetes. It allows us to artificially inject faults into a running system.
* **Why we used it:** How do we prove our self-healing AI works if the system never breaks? Chaos Mesh allows us to run commands like *"Throttle the CPU on the checkout service to 100% for 5 minutes"* or *"Randomly delete the frontend pod"*. This triggers the anomalies that our AI will detect and fix.

## Automation: Helm & PowerShell
* **Helm:**
  * **What it is:** The package manager for Kubernetes.
  * **Why we used it:** Deploying Prometheus, Grafana, Loki, and Chaos Mesh manually would require writing thousands of lines of complex YAML configuration. Helm allows us to install these massive, production-grade tools with single-line commands in our script.
* **PowerShell (`setup_local.ps1`):**
  * **What it is:** The script I wrote to automate the local setup.
  * **Why we used it:** It ensures that building your local test environment is perfectly repeatable. You can destroy your local cluster, run the script, and be back up and running with the app, monitoring, and chaos mesh in 60 seconds.

## Cloud Provisioning: Terraform
I created the Azure provisioning scripts (`main.tf`, `variables.tf`, `outputs.tf`) inside the `terraform/azure/` folder.

* **What it is:** Terraform is an "Infrastructure as Code" (IaC) tool. It uses code to talk to the Azure Cloud and build servers automatically.
* **Why we used it:** When we are ready to move from your local RTX 5060 machine to the real Azure cloud, we don't want to click around the Azure web portal manually trying to configure a Kubernetes cluster (AKS). Running this Terraform script will automatically create the resource group, spin up the VMs, configure the AKS cluster, and output the connection credentials securely in minutes.
