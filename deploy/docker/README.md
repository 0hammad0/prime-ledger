# Prime Ledger custom Docker image

Production can run stock `frappe/erpnext` from Docker Hub with hot-patches
(`patch-portal.sh`, `brand.sh`) on every deploy, **or** a custom image that
bakes branding + portal into the image.

## Hot-patch path (default CI)

```bash
yarn build:portal
bash deploy/ec2/sync-portal-patches.sh
# commit deploy/ec2/patches/portal — CI rsyncs deploy/ec2 and remote-deploy runs patch-portal.sh
```

## Optional: custom image

```bash
yarn build:portal
bash deploy/ec2/sync-portal-patches.sh
docker build -f deploy/docker/Dockerfile -t prime-ledger/erpnext:v16.29.0 .

# on EC2 .env:
#   CUSTOM_IMAGE=prime-ledger/erpnext:v16.29.0
```

`compose.brand-image.yaml` swaps the image when `CUSTOM_IMAGE` is set.

Portal URL after migrate + seed: `/portal`
