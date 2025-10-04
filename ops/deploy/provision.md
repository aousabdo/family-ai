# Lightsail / EC2 Provisioning Guide

## 1. Create the instance
- Choose a small Ubuntu 22.04 LTS Lightsail/EC2 instance (1–2 GB RAM is sufficient for MVP).
- Attach a static IP and note the public IPv4 address.
- Add an entry in your DNS provider for `DOMAIN` pointing to the instance IP (A record).

## 2. Harden the server
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

## 3. Install Docker & Compose
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install docker compose plugin
sudo apt-get install -y docker-compose-plugin
```

## 4. Prepare application directory
```bash
mkdir -p /opt/family-ai
cd /opt/family-ai
```
- Copy the repository content (via `git clone` or `scp`).
- Place the `.env` file in `/opt/family-ai/.env` and review all secrets.
- Ensure the certbot script is executable:
  ```bash
  chmod +x ops/certbot/init_renew.sh ops/backup/backup_to_s3.sh
  ```

## 5. Prime volumes & run stack
```bash
sudo docker compose pull
sudo docker compose build
sudo docker compose up -d
```
- Verify containers with `docker compose ps`.
- Once the stack is live, run an initial certificate issuance:
  ```bash
  sudo docker compose run --rm certbot
  sudo docker compose exec nginx nginx -s reload
  ```

## 6. Seed knowledge base (optional)
```bash
sudo docker compose exec server python -m app.scripts.seed_sample
```
(Replace with your own ingestion command to pull `/sample_corpus`).

## 7. Configure automatic start with systemd
```bash
sudo cp ops/deploy/systemd-family-ai.service /etc/systemd/system/family-ai.service
sudo systemctl daemon-reload
sudo systemctl enable family-ai.service
sudo systemctl start family-ai.service
```
- Check logs: `journalctl -u family-ai.service -f`.

## 8. Backups
- Ensure `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `S3_BUCKET_CORPUS` are set.
- Confirm cron is running inside the `backup` container: `docker compose logs backup`.

## 9. Post-deploy validation
- Visit `https://DOMAIN` to verify the web app.
- Use `/chat` to verify API connectivity.
- Confirm TLS certificate files exist in `certbot_conf` volume.

## 10. Preparing for RDS / App Runner
- When ready, point `DATABASE_URL` to RDS and remove the `db` service from compose.
- Deploy `server` to App Runner by building the Docker image and pushing to ECR. Update `NEXT_PUBLIC_API_BASE_URL` to the App Runner endpoint.
