import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workspaceRoot = path.resolve(__dirname, '..');

const gatewayHost = process.env.GATEWAY_HOST || '127.0.0.1';
const gatewayPort = Number(process.env.GATEWAY_PORT || 8080);
const apiPrefix = normalizePrefix(process.env.API_PREFIX || '/ai-search');
const backendOrigin = new URL(process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000');
const staticDir = path.resolve(
  process.env.STATIC_DIR || path.join(workspaceRoot, 'frontend', 'dist'),
);
const gatewayUser = process.env.GATEWAY_USER || '';
const gatewayPassword = process.env.GATEWAY_PASSWORD || '';

const mimeTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.gif', 'image/gif'],
  ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.webp', 'image/webp'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
]);

const hopByHopHeaders = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

const server = http.createServer((request, response) => {
  const requestUrl = new URL(request.url || '/', 'http://gateway.local');

  if (requestUrl.pathname === '/healthz') {
    sendText(response, 200, 'ok');
    return;
  }

  if (!isAuthorized(request)) {
    response.writeHead(401, {
      'content-type': 'text/plain; charset=utf-8',
      'www-authenticate': 'Basic realm="EGC Agent"',
    });
    response.end('Authentication required');
    return;
  }

  if (
    requestUrl.pathname === apiPrefix ||
    requestUrl.pathname.startsWith(`${apiPrefix}/`)
  ) {
    proxyApiRequest(request, response, requestUrl);
    return;
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    sendText(response, 404, 'Not found');
    return;
  }

  serveStaticFile(request, response, requestUrl);
});

server.listen(gatewayPort, gatewayHost, () => {
  console.log(`EGC gateway listening on http://${gatewayHost}:${gatewayPort}`);
  console.log(`Serving static files from ${staticDir}`);
  console.log(`Proxying ${apiPrefix}/* to ${backendOrigin.origin}`);
  if (gatewayUser && gatewayPassword) {
    console.log('Gateway Basic Auth is enabled.');
  } else {
    console.log('Gateway Basic Auth is disabled.');
  }
});

server.on('error', (error) => {
  console.error(`Gateway failed: ${error.message}`);
  process.exitCode = 1;
});

function normalizePrefix(value) {
  const trimmed = String(value || '').trim();
  if (!trimmed || trimmed === '/') {
    return '';
  }
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}`;
}

function isAuthorized(request) {
  if (!gatewayUser || !gatewayPassword) {
    return true;
  }

  const expected = `Basic ${Buffer.from(`${gatewayUser}:${gatewayPassword}`).toString('base64')}`;
  return request.headers.authorization === expected;
}

function proxyApiRequest(clientRequest, clientResponse, requestUrl) {
  const rewrittenPath = requestUrl.pathname.slice(apiPrefix.length) || '/';
  const backendPath = `${backendOrigin.pathname.replace(/\/$/, '')}${rewrittenPath}`;
  const backendUrl = new URL(backendOrigin.href);
  backendUrl.pathname = backendPath;
  backendUrl.search = requestUrl.search;

  const headers = { ...clientRequest.headers };
  for (const header of hopByHopHeaders) {
    delete headers[header];
  }

  headers.host = backendUrl.host;
  headers['x-forwarded-host'] = clientRequest.headers.host || '';
  headers['x-forwarded-proto'] = clientRequest.headers['x-forwarded-proto'] || 'http';
  headers['x-forwarded-for'] = [
    clientRequest.socket.remoteAddress,
    clientRequest.headers['x-forwarded-for'],
  ]
    .filter(Boolean)
    .join(', ');

  const transport = backendUrl.protocol === 'https:' ? https : http;
  const upstreamRequest = transport.request(
    {
      protocol: backendUrl.protocol,
      hostname: backendUrl.hostname,
      port: backendUrl.port || (backendUrl.protocol === 'https:' ? 443 : 80),
      method: clientRequest.method,
      path: `${backendUrl.pathname}${backendUrl.search}`,
      headers,
    },
    (upstreamResponse) => {
      const responseHeaders = { ...upstreamResponse.headers };
      for (const header of hopByHopHeaders) {
        delete responseHeaders[header];
      }

      clientResponse.writeHead(upstreamResponse.statusCode || 502, responseHeaders);
      upstreamResponse.pipe(clientResponse);
    },
  );

  upstreamRequest.on('error', (error) => {
    console.error(`Backend proxy error: ${error.message}`);
    if (!clientResponse.headersSent) {
      sendText(clientResponse, 502, 'Backend unavailable');
    } else {
      clientResponse.destroy(error);
    }
  });

  clientRequest.pipe(upstreamRequest);
}

function serveStaticFile(request, response, requestUrl) {
  const candidate = getStaticCandidate(requestUrl.pathname);

  fs.stat(candidate, (statError, stats) => {
    if (!statError && stats.isDirectory()) {
      sendFile(request, response, path.join(candidate, 'index.html'));
      return;
    }

    if (!statError && stats.isFile()) {
      sendFile(request, response, candidate);
      return;
    }

    sendFile(request, response, path.join(staticDir, 'index.html'));
  });
}

function getStaticCandidate(urlPathname) {
  let decodedPath;
  try {
    decodedPath = decodeURIComponent(urlPathname);
  } catch {
    decodedPath = '/';
  }

  const safeRelativePath = decodedPath
    .replace(/\\/g, '/')
    .replace(/^\/+/, '')
    .split('/')
    .filter((part) => part && part !== '..')
    .join(path.sep);

  return path.join(staticDir, safeRelativePath);
}

function sendFile(request, response, filePath) {
  const relativePath = path.relative(staticDir, filePath);
  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    sendText(response, 403, 'Forbidden');
    return;
  }

  fs.stat(filePath, (statError, stats) => {
    if (statError || !stats.isFile()) {
      sendText(response, 404, 'Not found');
      return;
    }

    const extension = path.extname(filePath).toLowerCase();
    const cacheControl = relativePath.startsWith(`assets${path.sep}`)
      ? 'public, max-age=31536000, immutable'
      : 'no-cache';

    response.writeHead(200, {
      'cache-control': cacheControl,
      'content-length': stats.size,
      'content-type': mimeTypes.get(extension) || 'application/octet-stream',
    });

    if (request.method === 'HEAD') {
      response.end();
      return;
    }

    fs.createReadStream(filePath).pipe(response);
  });
}

function sendText(response, statusCode, body) {
  response.writeHead(statusCode, {
    'content-type': 'text/plain; charset=utf-8',
    'content-length': Buffer.byteLength(body),
  });
  response.end(body);
}
