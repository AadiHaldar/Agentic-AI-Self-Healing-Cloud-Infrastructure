param (
    [switch]$InstallMonitoring = $true,
    [switch]$InstallChaosMesh = $true,
    [switch]$InstallApp = $true
)

Write-Host "Checking for kubectl and helm..." -ForegroundColor Cyan
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Error "kubectl is not installed. Please install it first."
    exit 1
}
if (!(Get-Command helm -ErrorAction SilentlyContinue)) {
    Write-Error "helm is not installed. Please install it first."
    exit 1
}

# Add necessary Helm repos
Write-Host "Adding Helm repositories..." -ForegroundColor Cyan
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

if ($InstallMonitoring) {
    Write-Host "Installing Prometheus & Grafana stack..." -ForegroundColor Cyan
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
    
    Write-Host "Installing Loki stack (Logs)..." -ForegroundColor Cyan
    helm upgrade --install loki grafana/loki-stack --namespace monitoring --set grafana.enabled=false,prometheus.enabled=false
}

if ($InstallChaosMesh) {
    Write-Host "Installing Chaos Mesh..." -ForegroundColor Cyan
    kubectl create namespace chaos-mesh --dry-run=client -o yaml | kubectl apply -f -
    helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh --namespace chaos-mesh --set chaosDaemon.runtime=containerd --set chaosDaemon.socketPath=/run/containerd/containerd.sock
}

if ($InstallApp) {
    Write-Host "Deploying Online Boutique App..." -ForegroundColor Cyan
    kubectl create namespace online-boutique --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -f .\infrastructure\k8s\app\online-boutique.yaml -n online-boutique
}

Write-Host "Local cluster setup complete!" -ForegroundColor Green
