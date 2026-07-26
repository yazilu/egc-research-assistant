# Cloudflare Tunnel setup

This shares the local EGC app through one public HTTPS URL without buying a
server. Use the named tunnel path for real use. The quick tunnel path is only a
short smoke test because this app uses streaming responses.

## 1. Confirm the backend is running

The backend should answer at:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/docs -UseBasicParsing
```

If it is not running, start the existing backend stack first:

```powershell
cd backend
docker compose up -d --build
```

## 2. Start the local gateway

Open a PowerShell terminal from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-gateway.ps1
```

Optional password gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-gateway.ps1 -GatewayUser egc -GatewayPassword "change-this-password"
```

Keep this terminal open. The gateway serves `frontend/dist` and proxies
`/ai-search/*` to the FastAPI backend.

## 3. Start a named Cloudflare Tunnel

Recommended for a few real users.

In Cloudflare Zero Trust:

1. Create a Cloudflare Tunnel.
2. Choose the cloudflared connector option.
3. Add a public hostname for the app.
4. If you run the local `cloudflared.exe` connector, set the service URL to:

```text
http://127.0.0.1:8080
```

If you run the Docker connector, set the service URL to:

```text
http://host.docker.internal:8080
```

5. Copy the tunnel token.

Then run this from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-cloudflare-named-tunnel.ps1
```

Paste the token when prompted.

Use the public hostname that you configured in Cloudflare.

To start the gateway and the named tunnel together in the background:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-fixed-domain-site.ps1
```

It uses the default gateway login:

```text
username: egc
password: xzc123456
```

## Optional: quick tunnel smoke test

Open a second PowerShell terminal from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-cloudflare-tunnel.ps1
```

If Docker cannot pull the Cloudflare image, download `cloudflared.exe` into
`tools/bin/cloudflared.exe`, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-cloudflare-local-tunnel.ps1
```

The script prints a public URL like:

```text
https://example.trycloudflare.com
```

Share that URL with the people who should use the app.

Quick tunnels are good for confirming that the page opens. For normal use, use
the named tunnel above so streaming chat responses are not blocked by quick
tunnel limitations.

## Stop sharing

Stop the local gateway with `Ctrl+C`, then stop the tunnel:

```powershell
docker compose -f .\tools\docker-compose.tunnel.yml down
docker compose -f .\tools\docker-compose.tunnel-token.yml down
powershell -ExecutionPolicy Bypass -File .\tools\stop-shared-site.ps1
```

## Notes

- The quick tunnel URL usually changes when the tunnel restarts.
- Anyone with the URL can reach the site unless you enable the optional gateway
  password or add Cloudflare Access on a named tunnel.
- Do not expose PostgreSQL, Elasticsearch, or FastAPI ports directly to the
  public internet.
