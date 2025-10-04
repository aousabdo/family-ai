#!/bin/sh
set -eu

if [ -z "${DOMAIN:-}" ]; then
  echo "DOMAIN environment variable is required for certbot" >&2
  exit 1
fi

if [ -z "${LETSENCRYPT_EMAIL:-}" ]; then
  echo "LETSENCRYPT_EMAIL environment variable is required for certbot" >&2
  exit 1
fi

if [ ! -d "/var/www/certbot" ]; then
  mkdir -p /var/www/certbot
fi

if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  certbot certonly \
    --non-interactive \
    --agree-tos \
    --email "$LETSENCRYPT_EMAIL" \
    --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN"
fi

while true; do
  certbot renew --webroot -w /var/www/certbot --quiet
  sleep 43200 # 12 hours
done
