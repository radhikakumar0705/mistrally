#!/usr/bin/env bash
# Builds a local Kubernetes cluster with kind and installs sockRat with Helm:
# ingress-nginx, cert-manager with a local CA, and the chart with HTTPS on https://localhost:8443.
# Needs docker, kind, kubectl and helm on PATH. Re-running it is safe.
#
#   deploy/kind/setup.sh           # create the cluster and install
#   deploy/kind/setup.sh --argocd  # also install Argo CD and hand the release over to it
set -euo pipefail

cd "$(dirname "$0")/../.."
CLUSTER=sockrat
CONTEXT=kind-$CLUSTER
INGRESS_NGINX=v1.11.3
CERT_MANAGER=v1.21.2
ARGOCD=v3.5.5

# Images are pulled on the host and loaded into the node: kind nodes can't always pull
# themselves (e.g. IPv6-only DNS answers on some networks), and local images never are pullable.
load() {
  for image in "$@"; do
    docker image inspect "$image" >/dev/null 2>&1 || docker pull -q "$image"
  done
  kind load docker-image --name "$CLUSTER" "$@"
}

if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --config deploy/kind/kind-config.yaml
fi
kubectl config use-context "$CONTEXT"

echo "==> Building application images"
docker build -q -t sockrat-backend:local backend
docker build -q -t sockrat-frontend:local frontend
docker build -q -t sockrat-sandbox:local sandbox
load sockrat-backend:local sockrat-frontend:local sockrat-sandbox:local \
  mysql:8.0.40 chromadb/chroma:1.3.5 redis:7.4.1-alpine

echo "==> ingress-nginx $INGRESS_NGINX"
load "registry.k8s.io/ingress-nginx/controller:$INGRESS_NGINX" \
  registry.k8s.io/ingress-nginx/kube-webhook-certgen:v1.4.4
# The upstream manifest pins image digests of the multi-arch index, which loaded images lack
curl -sSfL "https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-$INGRESS_NGINX/deploy/static/provider/kind/deploy.yaml" \
  | sed -E 's/@sha256:[a-f0-9]+//' | kubectl apply -f - >/dev/null
kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=300s

echo "==> cert-manager $CERT_MANAGER"
load "quay.io/jetstack/cert-manager-cainjector:$CERT_MANAGER" \
  "quay.io/jetstack/cert-manager-controller:$CERT_MANAGER" \
  "quay.io/jetstack/cert-manager-webhook:$CERT_MANAGER"
kubectl apply -f "https://github.com/cert-manager/cert-manager/releases/download/$CERT_MANAGER/cert-manager.yaml" >/dev/null
kubectl -n cert-manager wait --for=condition=available deployment --all --timeout=300s
# The webhook can take a few more seconds to accept requests after it reports ready
for _ in 1 2 3 4 5 6; do
  kubectl apply -f deploy/cert-manager/local-ca.yaml >/dev/null && break
  sleep 5
done
kubectl wait --for=condition=ready clusterissuer/sockrat-ca --timeout=120s

if [[ "${1:-}" == "--argocd" ]]; then
  echo "==> Argo CD $ARGOCD"
  manifest=$(curl -sSfL "https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD/manifests/install.yaml")
  # shellcheck disable=SC2046  # one argument per image
  load $(grep -oE 'image: *[^ ]+' <<<"$manifest" | awk '{print $2}' | sort -u)
  kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  kubectl apply -n argocd --server-side --force-conflicts -f - <<<"$manifest" >/dev/null
  kubectl -n argocd wait --for=condition=available deployment --all --timeout=600s
  kubectl apply -n argocd -f deploy/argocd/application.yaml
  echo "Argo CD now syncs helm/sockrat from GitHub. UI:"
  echo "  kubectl -n argocd port-forward svc/argocd-server 8081:443"
  echo "  password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
else
  echo "==> sockRat"
  helm upgrade --install sockrat helm/sockrat -n sockrat --create-namespace \
    -f helm/sockrat/values-kind.yaml --kube-context "$CONTEXT" --wait --timeout 10m
fi

echo
echo "Open https://localhost:8443 (certificate from the local CA; trust it with:"
echo "  kubectl -n cert-manager get secret sockrat-ca -o jsonpath='{.data.ca\\.crt}' | base64 -d > sockrat-ca.crt)"
