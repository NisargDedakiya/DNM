const toHeaders = (apiKey) => {
  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  return headers;
};

export class NisargHunterJSClient {
  constructor({ baseUrl, apiKey = null, websocketUrl = null }) {
    this.baseUrl = String(baseUrl).replace(/\/$/, '');
    this.apiKey = apiKey;
    this.websocketUrl = websocketUrl;
  }

  authenticate(apiKey) {
    this.apiKey = apiKey;
    return this;
  }

  async _get(path, params = {}) {
    const query = new URLSearchParams(params).toString();
    const response = await fetch(`${this.baseUrl}${path}?${query}`, {
      method: 'GET',
      headers: toHeaders(this.apiKey),
    });
    return response.json();
  }

  async fetchFindings(organizationId, page = 1, pageSize = 20) {
    return this._get('/public/findings', {
      organization_id: organizationId,
      page,
      page_size: pageSize,
    });
  }

  async fetchAttackPaths(organizationId, page = 1, pageSize = 20) {
    return this._get('/public/attack-paths', {
      organization_id: organizationId,
      page,
      page_size: pageSize,
    });
  }

  subscribeRealtime(onMessage, { websocketPath = '/ws/public-events' } = {}) {
    const socketUrl = (this.websocketUrl || this.baseUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')).replace(/\/$/, '') + websocketPath;
    const socket = new WebSocket(socketUrl);
    socket.onopen = () => {
      if (this.apiKey) {
        socket.send(JSON.stringify({ type: 'authenticate', api_key: this.apiKey }));
      }
    };
    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch (error) {
        onMessage({ raw: event.data, error: String(error) });
      }
    };
    return socket;
  }
}

export function authenticate(baseUrl, apiKey, websocketUrl = null) {
  return new NisargHunterJSClient({ baseUrl, apiKey, websocketUrl });
}

export async function fetchFindings(client, organizationId, page = 1, pageSize = 20) {
  return client.fetchFindings(organizationId, page, pageSize);
}

export async function fetchAttackPaths(client, organizationId, page = 1, pageSize = 20) {
  return client.fetchAttackPaths(organizationId, page, pageSize);
}

export function subscribeRealtime(client, onMessage, options = {}) {
  return client.subscribeRealtime(onMessage, options);
}

if (typeof module !== 'undefined') {
  module.exports = {
    NisargHunterJSClient,
    authenticate,
    fetchFindings,
    fetchAttackPaths,
    subscribeRealtime,
  };
}
