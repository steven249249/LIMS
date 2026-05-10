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
	@command -v helm >/dev/null || { echo "helm not found — install: https://helm.sh/docs/intro/install/"; exit 1; }
	helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
	helm repo update bitnami
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm upgrade --install lims-mysql bitnami/mysql -n $(NAMESPACE) \
	  --set auth.rootPassword=kind-mysql-root \
	  --set auth.database=lab_booking \
	  --set primary.persistence.size=1Gi
	helm upgrade --install lims-redis bitnami/redis -n $(NAMESPACE) \
	  --set auth.enabled=false \
	  --set master.persistence.size=1Gi

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
