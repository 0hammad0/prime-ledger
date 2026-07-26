# Prime Ledger custom Docker image

Production currently runs stock `frappe/erpnext` from Docker Hub, then applies white-label via `deploy/ec2/brand.sh` on every deploy.

## Optional: branded image

```bash
# from repo root
docker build -f deploy/docker/Dockerfile -t prime-ledger/erpnext:v16.29.0 .

# on EC2, retag / push to a registry you control, then set in ~/deploy-ec2/.env:
#   CUSTOM_IMAGE=prime-ledger/erpnext:v16.29.0
```

`compose.brand-image.yaml` swaps the image for backend/frontend/workers when `CUSTOM_IMAGE` is set.

Site settings (app name, navbar cleanup, CSS link) still come from `brand.sh`.
