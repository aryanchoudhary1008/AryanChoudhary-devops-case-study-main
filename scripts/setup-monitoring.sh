#!/usr/bin/env bash
# Task 4: install Prometheus + Grafana (kube-prometheus-stack) and wire up the FinVeritas dashboard.
# Prerequisites: kubectl pointing at the cluster, helm. Run from the repository root.
set -euo pipefail

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f monitoring/kube-prometheus-values.yaml --wait

kubectl apply -f monitoring/servicemonitor.yaml
kubectl apply -f monitoring/prometheus-rules.yaml
kubectl apply -f monitoring/grafana-dashboard-configmap.yaml

echo "Prometheus: http://localhost:9090   (Status > Targets should list finveritas-api)"
echo "Grafana:    http://localhost:3000   (admin / admin) > Dashboards > FinVeritas Ratio Service"
