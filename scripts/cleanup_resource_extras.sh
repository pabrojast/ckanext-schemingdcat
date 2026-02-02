#!/usr/bin/env bash
set -euo pipefail

SQL_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cleanup_resource_extras.sql"

APPLY=0
MAX_BYTES=50000
PRUNE_BY_SIZE=1
DROP_KEYS="text_content_info,data_fields,data_statistics,data_domains,compression_info,file_integrity,format_version,document_pages,spreadsheet_sheets,content_type_detected,geographic_coverage,administrative_boundaries"

NAMESPACE="ckan"
POD=""
USE_K8S=0
KUBECONFIG_PATH=""
KUBE_CONTEXT=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --apply                 Apply updates (default: dry run)
  --max-bytes N           Max bytes per field before pruning (default: 50000)
  --no-size-prune         Do not prune by size (only drop keys)
  --drop-keys "k1,k2"     Comma-separated keys to drop (default: curated list)
  --k8s                   Run inside Kubernetes (auto-pick a ckan-* pod)
  --kubeconfig PATH       Path to kubeconfig file (optional)
  --context NAME          Kubernetes context name (optional)
  --namespace NS          Kubernetes namespace (default: ckan)
  --pod POD               Kubernetes pod name (overrides auto-pick)
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --max-bytes)
      MAX_BYTES="${2:-}"
      shift 2
      ;;
    --no-size-prune)
      PRUNE_BY_SIZE=0
      shift
      ;;
    --drop-keys)
      DROP_KEYS="${2:-}"
      shift 2
      ;;
    --k8s)
      USE_K8S=1
      shift
      ;;
    --kubeconfig)
      KUBECONFIG_PATH="${2:-}"
      USE_K8S=1
      shift 2
      ;;
    --context)
      KUBE_CONTEXT="${2:-}"
      USE_K8S=1
      shift 2
      ;;
    --namespace)
      NAMESPACE="${2:-}"
      shift 2
      ;;
    --pod)
      POD="${2:-}"
      USE_K8S=1
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run_psql_local() {
  if [[ ! -f "$SQL_FILE" ]]; then
    echo "SQL file not found: $SQL_FILE" >&2
    exit 1
  fi
  if [[ -z "${CKAN_SQLALCHEMY_URL:-}" ]]; then
    echo "CKAN_SQLALCHEMY_URL is required for local run. Use --k8s to run in cluster." >&2
    exit 1
  fi
  psql "$CKAN_SQLALCHEMY_URL" \
    -v apply="$APPLY" \
    -v max_bytes="$MAX_BYTES" \
    -v prune_by_size="$PRUNE_BY_SIZE" \
    -v drop_keys="$DROP_KEYS" \
    -f "$SQL_FILE"
}

pick_pod() {
  kubectl -n "$NAMESPACE" get pods --no-headers \
    | awk '$1 ~ /^ckan-/ && $3 == "Running" {print $1; exit}'
}

run_psql_k8s() {
  if ! command -v kubectl >/dev/null 2>&1; then
    echo "kubectl not found in PATH" >&2
    exit 1
  fi

  if [[ -n "$KUBECONFIG_PATH" ]]; then
    export KUBECONFIG="$KUBECONFIG_PATH"
  fi
  if [[ -n "$KUBE_CONTEXT" ]]; then
    kubectl config use-context "$KUBE_CONTEXT" >/dev/null
  fi

  if ! kubectl version --request-timeout=5s >/dev/null 2>&1; then
    echo "kubectl cannot reach the cluster. Check kubeconfig/context." >&2
    if kubectl config current-context >/dev/null 2>&1; then
      echo "Current context: $(kubectl config current-context)" >&2
    fi
    if [[ -n "${KUBECONFIG:-}" ]]; then
      echo "KUBECONFIG: ${KUBECONFIG}" >&2
    fi
    exit 1
  fi

  if [[ -z "$POD" ]]; then
    POD="$(pick_pod)"
  fi
  if [[ -z "$POD" ]]; then
    echo "No running ckan-* pod found in namespace $NAMESPACE" >&2
    exit 1
  fi
  kubectl -n "$NAMESPACE" exec "$POD" -- sh -c \
    "psql \"\$CKAN_SQLALCHEMY_URL\" \
      -v apply=$APPLY \
      -v max_bytes=$MAX_BYTES \
      -v prune_by_size=$PRUNE_BY_SIZE \
      -v drop_keys=\"$DROP_KEYS\" \
      -f /app/src/ckanext-schemingdcat/scripts/cleanup_resource_extras.sql"
}

if [[ "$USE_K8S" -eq 1 ]]; then
  run_psql_k8s
else
  run_psql_local
fi
