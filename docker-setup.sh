#!/usr/bin/env bash
set -euo pipefail

echo "==> Updating apt..."
sudo apt-get update -y

echo "==> Installing Docker + Compose v2..."
sudo apt-get install -y docker.io docker-compose-v2

echo "==> Enabling Docker service..."
sudo systemctl enable --now docker

echo "==> Adding user '$USER' to docker group..."
sudo usermod -aG docker "$USER"

echo "==> Versions:"
sudo docker --version
sudo docker compose version

echo ""
echo "Done. Run 'newgrp docker' (or log out & back in) to use docker without sudo."