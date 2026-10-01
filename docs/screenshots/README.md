# Screenshots

Evidence for the practical tasks. Save each image in this folder with the file name below.

| File | Task | What to capture | Command |
|---|---|---|---|
| `task1-pipeline-run.png` | 1 | Successful GitHub Actions run with all four jobs green | GitHub → Actions → CI/CD Pipeline |
| `task2-ansible-run.png` | 2 | `PLAY RECAP` of the playbook (`failed=0`) and the health message | `ansible-playbook playbook.yml -K` |
| `task3-pods-v1.png` | 3 | Three pods running v1 | `kubectl -n finveritas get pods -o wide` |
| `task3-rolling-update.png` | 3 | Rollout to v2 completing | `kubectl -n finveritas rollout status deployment/finveritas-api` |
| `task3-rollout-history.png` | 3 | Revision history with change causes | `kubectl -n finveritas rollout history deployment/finveritas-api` |
| `task3-rollback.png` | 3 | `rollout undo` and `/health` showing v1 again | `kubectl -n finveritas rollout undo deployment/finveritas-api` |
| `task4-prometheus-targets.png` | 4 | `finveritas-api` target UP | http://localhost:9090/targets |
| `task4-grafana-dashboard.png` | 4 | Dashboard with uptime, latency and error-rate panels | http://localhost:3000 |
| `task4-chaos-error-rate.png` | 4 | Error-rate panel during a `FAULT_RATE` experiment | edit `k8s/configmap.yaml`, restart deployment |
