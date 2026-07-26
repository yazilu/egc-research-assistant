# Tailscale Funnel setup

This shares the local EGC app through a fixed free `*.ts.net` HTTPS address.
The site still runs on this computer, so the address only works while the
computer is powered on, online, and Tailscale is connected.

## 1. Install and sign in to Tailscale

Install Tailscale for Windows, then sign in to your Tailscale account.

If you use the CLI, this command opens a login URL:

```powershell
tailscale up --hostname=egc-agent
```

In the Tailscale admin console, enable Funnel for your tailnet if it is not
already enabled.

Required admin-console switches:

- Go to **DNS** and enable **MagicDNS**.
- Go to **DNS** and enable **HTTPS Certificates**.
- Go to **Access controls**, expand **Funnel**, then add Funnel to the policy.

Funnel requires valid HTTPS certificates and a Funnel node attribute in the
tailnet policy.

## 2. Start the fixed address

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start-tailscale-funnel.ps1
```

The default login gate is:

```text
username: egc
password: xzc123456
```

To see the public URL:

```powershell
tailscale funnel status
```

The URL should look like:

```text
https://egc-agent.<your-tailnet>.ts.net
```

## Stop sharing

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\stop-tailscale-funnel.ps1
```
