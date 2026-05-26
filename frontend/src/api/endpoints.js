export const ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    LOGOUT: '/api/v1/auth/logout',
    ME: '/api/v1/auth/me',
  },
  FINDINGS: {
    LIST: '/api/v1/findings',
    DETAILS: (id) => `/api/v1/findings/${id}`,
    APPROVE: (id) => `/api/v1/findings/${id}/approve`,
  },
  HUNTS: {
    LIST: '/api/v1/hunts',
    START: '/api/v1/hunts/start',
    STATUS: (id) => `/api/v1/hunts/${id}/status`,
  },
  GRAPH: {
    DATA: '/api/v1/graph/data',
    PATH: '/api/v1/graph/path',
  },
  CHAT: {
    MESSAGE: '/api/v1/hunt-chat/message',
    SESSION: '/api/v1/hunt-chat/session',
  },
  SCHEDULER: {
    LIST: '/api/v1/scheduler/hunts',
    CREATE: '/api/v1/scheduler/hunt',
  }
};
