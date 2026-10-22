#!/usr/bin/env bash
# Sets up (or updates) the live demo on a fresh Ubuntu 22.04/24.04 VM, amd64 or arm64.
# Run it on the VM as a normal user with sudo:
#
#   curl -fsSL https://raw.githubusercontent.com/radhikakumar0705/sockrat/master/deploy/demo/setup-vm.sh | bash
#
# or, from a checkout, deploy/demo/setup-vm.sh [git-ref]. Re-running it updates the code and restarts.
#
# Settings (environment variables, all optional):
#   SITE_ADDRESS  public hostname; defaults to <public-ip>.sslip.io, which needs no domain
#   REPO_REF      branch, tag or commit to deploy (default: master, or the first argument)
#
# The Groq API key is read from ~/sockrat.secrets, which you create yourself:
#   echo "GROQ_API_KEY=gsk_..." > ~/sockrat.secrets && chmod 600 ~/sockrat.secrets
set -euo pipefail

REPO_URL=https://github.com/radhikakumar0705/sockrat.git
APP_DIR="$HOME/sockrat"
REPO_REF="${1:-${REPO_REF:-master}}"
SECRETS_FILE="$HOME/sockrat.secrets"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

log() { printf '\n==> %s\n' "$*"; }

if [[ ! -f "$SECRETS_FILE" ]] || ! grep -q '^GROQ_API_KEY=.' "$SECRETS_FILE"; then
  echo "Create $SECRETS_FILE with your Groq API key first:" >&2
  echo "  echo \"GROQ_API_KEY=gsk_...\" > $SECRETS_FILE && chmod 600 $SECRETS_FILE" >&2
  exit 1
fi

if ! command -v docker >/dev/null; then
  log "Installing Docker"
  sudo apt-get update -q
  sudo apt-get install -y -q ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091  # provided by the OS
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -q
  sudo apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi
# The group change applies to new logins; use sudo for docker until then
docker info >/dev/null 2>&1 || COMPOSE=(sudo "${COMPOSE[@]}")

# Oracle Cloud's Ubuntu images reject incoming traffic except SSH in iptables, in addition to the
# VCN security list (open 80 and 443 there too, in the web console)
if sudo iptables -S INPUT 2>/dev/null | grep -q -- '-j REJECT'; then
  for port in 80 443; do
    sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
      || sudo iptables -I INPUT 5 -p tcp --dport "$port" -j ACCEPT
  done
  sudo iptables -C INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null \
    || sudo iptables -I INPUT 5 -p udp --dport 443 -j ACCEPT
  command -v netfilter-persistent >/dev/null && sudo netfilter-persistent save >/dev/null
fi

log "Fetching $REPO_REF"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone -q "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch -q origin
if git rev-parse -q --verify "origin/$REPO_REF" >/dev/null; then
  git checkout -q --detach "origin/$REPO_REF"   # a branch
else
  git checkout -q --detach "$REPO_REF"          # a tag or commit
fi
echo "Deploying $(git log --oneline -1)"

if [[ ! -f .env ]]; then
  log "Creating .env with generated secrets"
  site="${SITE_ADDRESS:-$(curl -fsS https://checkip.amazonaws.com | tr -d '[:space:]').sslip.io}"
  umask 077
  {
    echo "SECRET_KEY=$(openssl rand -hex 32)"
    echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"
    echo "SANDBOX_TOKEN=$(openssl rand -hex 32)"
    echo "MYSQL_PASSWORD=$(openssl rand -hex 24)"
    echo "MYSQL_ROOT_PASSWORD=$(openssl rand -hex 24)"
    echo "SITE_ADDRESS=$site"
    echo "PUBLIC_URL=https://$site"
    echo "COOKIE_SECURE=true"
    echo "LLM_PROVIDER=groq"
    echo "LLM_MODELS=llama-3.1-8b-instant,llama-3.3-70b-versatile"
    echo "WEB_CONCURRENCY=2"
  } > .env
fi

# The Groq key lives only in ~/sockrat.secrets; copy it into .env on every run so rotating it is
# just editing that file and re-running this script
grep -v '^GROQ_API_KEY=' .env > .env.tmp || true
grep '^GROQ_API_KEY=' "$SECRETS_FILE" >> .env.tmp
mv .env.tmp .env && chmod 600 .env

log "Building and starting (the first build takes several minutes)"
"${COMPOSE[@]}" up -d --build --remove-orphans
docker image prune -f >/dev/null 2>&1 || true

site=$(grep '^SITE_ADDRESS=' .env | cut -d= -f2)
log "Waiting for https://$site"
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null "https://$site/api/health/ready"; then
    echo "Live at https://$site"
    exit 0
  fi
  sleep 5
done
echo "Not reachable yet. Check that ports 80 and 443 are open in the cloud firewall, then:" >&2
echo "  cd $APP_DIR && ${COMPOSE[*]} logs caddy backend" >&2
exit 1
