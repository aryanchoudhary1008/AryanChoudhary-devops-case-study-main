#!/usr/bin/env bash
# Task 3 demo: deploy v1, roll out v2 with zero downtime, then roll back to v1.
# Prerequisites: docker, kind, kubectl. Run from the repository root:
#   bash scripts/rolling-update-demo.sh
set -euo pipefail

CLUSTER=finveritas
NS=finveritas
IMAGE=finveritas-api

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

step "Creating kind cluster (skipped if it already exists)"
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --config scripts/kind-config.yaml

step "Building image versions v1 and v2"
docker build -t "$IMAGE:v1" --build-arg APP_VERSION=v1 .
docker build -t "$IMAGE:v2" --build-arg APP_VERSION=v2 .
kind load docker-image "$IMAGE:v1" "$IMAGE:v2" --name "$CLUSTER"

step "Deploying v1"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml -f k8s/service.yaml
kubectl -n "$NS" set image deployment/finveritas-api api="$IMAGE:v1"
kubectl -n "$NS" annotate deployment/finveritas-api kubernetes.io/change-cause="deploy v1" --overwrite
kubectl -n "$NS" rollout status deployment/finveritas-api
kubectl -n "$NS" get pods -o wide
curl -s http://localhost:8080/health; echo

step "Rolling update to v2 (maxSurge=1, maxUnavailable=0)"
kubectl -n "$NS" set image deployment/finveritas-api api="$IMAGE:v2"
kubectl -n "$NS" annotate deployment/finveritas-api kubernetes.io/change-cause="rolling update to v2" --overwrite
kubectl -n "$NS" rollout status deployment/finveritas-api
kubectl -n "$NS" get pods -o wide
curl -s http://localhost:8080/health; echo

step "Rollout history"
kubectl -n "$NS" rollout history deployment/finveritas-api

step "Rolling back to the previous revision (v1)"
kubectl -n "$NS" rollout undo deployment/finveritas-api
kubectl -n "$NS" rollout status deployment/finveritas-api
kubectl -n "$NS" rollout history deployment/finveritas-api
curl -s http://localhost:8080/health; echo
