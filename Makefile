# Convenience targets for local Kubernetes validation.
#
# `make kind-up`        — create a kind cluster with NodePort exposed on :30080
# `make kind-deps`      — install bitnami MySQL + Redis (replaces Cloud SQL + Memorystore)
# `make kind-build`     — build the K8s images locally
# `make kind-load`      — load them into the kind cluster (no registry push)
# `make kind-deploy`    — helm install the LIMS chart with envs/local.yaml
# `make kind-status`    — show pods + recent events
# `make kind-down`      — delete the cluster
#
# `make kind-up && make kind-deps && make kind-build kind-load kind-deploy`
# is the full Step-2 validation cycle from the migration plan.

CLUSTER ?= lims-local
NAMESPACE ?= lims-local
TAG ?= local
BACKEND_IMG  ?= lims/backend:$(TAG)
FRONTEND_IMG ?= lims/frontend:$(TAG)

.PHONY: kind-up kind-down kind-deps kind-build kind-load kind-deploy kind-status kind-test backend-test

kind-up:
	@command -v kind >/dev/null || { echo "kind not found — install: go install sigs.k8s.io/kind@latest"; exit 1; }
	@kind get clusters | grep -q '^$(CLUSTER)$$' && echo "cluster $(CLUSTER) already exists" \
	  || kind create cluster --name $(CLUSTER) --config scripts/kind-config.yaml

kind-down:
	kind delete cluster --name $(CLUSTER)

kind-deps:
	# Plain mysql:8.0 + redis:7-alpine StatefulSet/Deployment. Avoids the
	# bitnami helm chart because their public Docker Hub mirror was
	# discontinued and the secured images require a paid login. For local
	# kind validation a self-contained manifest is enough.
	kubectl apply -f scripts/kind-deps.yaml
	kubectl wait --for=condition=Ready pod -l app=lims-mysql -n $(NAMESPACE) --timeout=180s
	kubectl wait --for=condition=Ready pod -l app=lims-redis -n $(NAMESPACE) --timeout=60s

kind-deps-down:
	# Tear down a previous bitnami install (if any) + the new manifests.
	helm uninstall lims-mysql -n $(NAMESPACE) 2>/dev/null || true
	helm uninstall lims-redis -n $(NAMESPACE) 2>/dev/null || true
	kubectl delete -f scripts/kind-deps.yaml --ignore-not-found

kind-build:
	docker build -f backend/Dockerfile.k8s -t $(BACKEND_IMG) backend/
	docker build -f frontend/Dockerfile.k8s --build-arg VITE_API_BASE=/api \
	  -t $(FRONTEND_IMG) frontend/

kind-load:
	kind load docker-image $(BACKEND_IMG) $(FRONTEND_IMG) --name $(CLUSTER)

kind-deploy:
	helm upgrade --install lims helm/lims/ \
	  --namespace $(NAMESPACE) --create-namespace \
	  -f helm/lims/envs/local.yaml \
	  --set image.tag=$(TAG) \
	  --wait --timeout 5m

kind-status:
	@echo '── pods ─────────────────────────────────────────'
	@kubectl get pods -n $(NAMESPACE) -o wide
	@echo
	@echo '── recent events ────────────────────────────────'
	@kubectl get events -n $(NAMESPACE) --sort-by=.lastTimestamp | tail -20

kind-test:
	@kubectl run --rm -i --restart=Never --image=curlimages/curl:8.11.1 -n $(NAMESPACE) probe -- \
	  sh -c 'curl -fsS http://lims-lims-backend:8000/healthz && echo && curl -fsS http://lims-lims-backend:8000/readyz'

backend-test:
	cd backend && pytest --no-header -q

# ─────────────────────────────────────────────────────────────────────────
# GCP cost-control helpers (demo / Scenario B)
# Set GCP_PROJECT before running, e.g.
#   GCP_PROJECT=lims-prod-2026-xxx make gcp-pause
# ─────────────────────────────────────────────────────────────────────────
GCP_PROJECT ?=
GCP_REGION  ?= asia-east1

gcp-pause:
	@test -n "$(GCP_PROJECT)" || { echo "set GCP_PROJECT=<project-id>"; exit 1; }
	# Stop Cloud SQL (you keep paying for storage but not vCPU/RAM).
	gcloud sql instances patch lims-prod-mysql \
	  --project=$(GCP_PROJECT) --activation-policy=NEVER --quiet
	# Scale all LIMS Deployments to 0 replicas (free up Autopilot pod billing).
	# Memorystore can't be paused — only destroyed/created. For ~$40/mo
	# Basic 1GB, leave it running.
	kubectl scale -n lims-prod deployment --all --replicas=0
	@echo "✓ Paused. To resume: make gcp-resume GCP_PROJECT=$(GCP_PROJECT)"

gcp-resume:
	@test -n "$(GCP_PROJECT)" || { echo "set GCP_PROJECT=<project-id>"; exit 1; }
	gcloud sql instances patch lims-prod-mysql \
	  --project=$(GCP_PROJECT) --activation-policy=ALWAYS --quiet
	# Wait until Cloud SQL is RUNNABLE before scaling pods (otherwise the
	# Cloud SQL Auth Proxy sidecar will crash-loop).
	until [ "$$(gcloud sql instances describe lims-prod-mysql --project=$(GCP_PROJECT) --format='value(state)')" = "RUNNABLE" ]; do \
	  echo "  waiting for Cloud SQL to start..."; sleep 10; \
	done
	# Scale pods back up to the values from helm/lims/envs/prod.yaml.
	# Argo CD selfHeal will also do this within a few minutes if you forget.
	kubectl scale -n lims-prod deployment lims-lims-backend --replicas=1
	kubectl scale -n lims-prod deployment lims-lims-frontend --replicas=1
	kubectl scale -n lims-prod deployment lims-lims-celery --replicas=1
	@echo "✓ Resumed."

gcp-destroy:
	@test -n "$(GCP_PROJECT)" || { echo "set GCP_PROJECT=<project-id>"; exit 1; }
	@echo "WARNING: this destroys EVERY GCP resource Terraform owns for prod."
	@echo "Press Ctrl-C in 10 seconds to abort..."; sleep 10
	cd infra/envs/prod && terraform destroy -auto-approve
	@echo "✓ Demo torn down. Verify in Cloud Console → Billing that costs stop."
