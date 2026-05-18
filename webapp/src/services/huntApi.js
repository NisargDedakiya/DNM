/**
 * Hunt API Service
 * Centralized API client for all hunting operations
 * Handles JWT auth, error handling, and request coordination
 */

import api from '../client';

export const huntApi = {
  /**
   * Get active hunts for organization
   * @param {string} organizationId - Organization ID
   * @param {Object} filters - Query filters
   * @returns {Promise<Array>}
   */
  async getActiveHunts(organizationId, filters = {}) {
    try {
      const response = await api.get('/hunts/active', {
        params: { organization_id: organizationId, ...filters },
      });
      return response.data?.hunts || [];
    } catch (error) {
      console.error('[HuntApi] Failed to fetch active hunts:', error);
      throw error;
    }
  },

  /**
   * Get critical findings
   * @param {string} organizationId - Organization ID
   * @param {Object} filters - Query filters
   * @returns {Promise<Array>}
   */
  async getCriticalFindings(organizationId, filters = {}) {
    try {
      const response = await api.get('/findings/critical', {
        params: { organization_id: organizationId, ...filters },
      });
      return response.data?.findings || [];
    } catch (error) {
      console.error('[HuntApi] Failed to fetch critical findings:', error);
      throw error;
    }
  },

  /**
   * Get all findings with filtering
   * @param {string} organizationId - Organization ID
   * @param {Object} filters - Query filters (severity, status, etc)
   * @returns {Promise<Object>}
   */
  async getFindings(organizationId, filters = {}) {
    try {
      const response = await api.get('/findings', {
        params: { organization_id: organizationId, ...filters },
      });
      return response.data || {};
    } catch (error) {
      console.error('[HuntApi] Failed to fetch findings:', error);
      throw error;
    }
  },

  /**
   * Get finding details
   * @param {string} findingId - Finding ID
   * @returns {Promise<Object>}
   */
  async getFindingDetails(findingId) {
    try {
      const response = await api.get(`/findings/${findingId}`);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to fetch finding details:', error);
      throw error;
    }
  },

  /**
   * Update finding status
   * @param {string} findingId - Finding ID
   * @param {string} status - New status
   * @param {string} notes - Optional notes
   * @returns {Promise<Object>}
   */
  async updateFindingStatus(findingId, status, notes = '') {
    try {
      const response = await api.put(`/findings/${findingId}/status`, {
        status,
        notes,
      });
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to update finding status:', error);
      throw error;
    }
  },

  /**
   * Add evidence to finding
   * @param {string} findingId - Finding ID
   * @param {Object} evidence - Evidence data
   * @returns {Promise<Object>}
   */
  async addEvidence(findingId, evidence) {
    try {
      const response = await api.post(`/findings/${findingId}/evidence`, evidence);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to add evidence:', error);
      throw error;
    }
  },

  /**
   * Get recon feed
   * @param {string} organizationId - Organization ID
   * @param {Object} filters - Query filters
   * @returns {Promise<Array>}
   */
  async getReconFeed(organizationId, filters = {}) {
    try {
      const response = await api.get('/recon/feed', {
        params: { organization_id: organizationId, ...filters },
      });
      return response.data?.events || [];
    } catch (error) {
      console.error('[HuntApi] Failed to fetch recon feed:', error);
      throw error;
    }
  },

  /**
   * Get hunt details
   * @param {string} huntId - Hunt ID
   * @returns {Promise<Object>}
   */
  async getHuntDetails(huntId) {
    try {
      const response = await api.get(`/hunts/${huntId}`);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to fetch hunt details:', error);
      throw error;
    }
  },

  /**
   * Get hunt progress/status
   * @param {string} huntId - Hunt ID
   * @returns {Promise<Object>}
   */
  async getHuntProgress(huntId) {
    try {
      const response = await api.get(`/hunts/${huntId}/progress`);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to fetch hunt progress:', error);
      throw error;
    }
  },

  /**
   * Start manual verification for finding
   * @param {string} findingId - Finding ID
   * @returns {Promise<Object>}
   */
  async startVerification(findingId) {
    try {
      const response = await api.post(`/findings/${findingId}/verify/start`, {});
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to start verification:', error);
      throw error;
    }
  },

  /**
   * Submit verification result
   * @param {string} findingId - Finding ID
   * @param {Object} verification - Verification data
   * @returns {Promise<Object>}
   */
  async submitVerification(findingId, verification) {
    try {
      const response = await api.post(
        `/findings/${findingId}/verify/submit`,
        verification
      );
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to submit verification:', error);
      throw error;
    }
  },

  /**
   * Get vulnerability intelligence
   * @param {string} vulnerability - CVE/CWE identifier
   * @returns {Promise<Object>}
   */
  async getVulnerabilityIntel(vulnerability) {
    try {
      const response = await api.get(`/intelligence/vulnerabilities/${vulnerability}`);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to fetch vulnerability intel:', error);
      throw error;
    }
  },

  /**
   * Get high-risk assets
   * @param {string} organizationId - Organization ID
   * @returns {Promise<Array>}
   */
  async getHighRiskAssets(organizationId) {
    try {
      const response = await api.get('/assets/high-risk', {
        params: { organization_id: organizationId },
      });
      return response.data?.assets || [];
    } catch (error) {
      console.error('[HuntApi] Failed to fetch high-risk assets:', error);
      throw error;
    }
  },

  /**
   * Get recon statistics
   * @param {string} organizationId - Organization ID
   * @returns {Promise<Object>}
   */
  async getReconStats(organizationId) {
    try {
      const response = await api.get('/recon/statistics', {
        params: { organization_id: organizationId },
      });
      return response.data || {};
    } catch (error) {
      console.error('[HuntApi] Failed to fetch recon stats:', error);
      throw error;
    }
  },

  /**
   * Get exposure analytics
   * @param {string} organizationId - Organization ID
   * @returns {Promise<Object>}
   */
  async getExposureAnalytics(organizationId) {
    try {
      const response = await api.get('/analytics/exposures', {
        params: { organization_id: organizationId },
      });
      return response.data || {};
    } catch (error) {
      console.error('[HuntApi] Failed to fetch exposure analytics:', error);
      throw error;
    }
  },

  /**
   * Generate report for finding
   * @param {string} findingId - Finding ID
   * @param {Object} options - Report options
   * @returns {Promise<Object>}
   */
  async generateReport(findingId, options = {}) {
    try {
      const response = await api.post(`/findings/${findingId}/report`, options);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to generate report:', error);
      throw error;
    }
  },

  /**
   * Get report preview
   * @param {string} findingId - Finding ID
   * @param {string} format - Report format (hackerone, bugcrowd, etc)
   * @returns {Promise<Object>}
   */
  async getReportPreview(findingId, format = 'hackerone') {
    try {
      const response = await api.get(`/findings/${findingId}/report/preview`, {
        params: { format },
      });
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to fetch report preview:', error);
      throw error;
    }
  },

  /**
   * Export report
   * @param {string} reportId - Report ID
   * @param {string} format - Export format (pdf, markdown, etc)
   * @returns {Promise<Blob>}
   */
  async exportReport(reportId, format = 'markdown') {
    try {
      const response = await api.get(`/reports/${reportId}/export`, {
        params: { format },
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to export report:', error);
      throw error;
    }
  },

  /**
   * Get AI recommendations
   * @param {string} organizationId - Organization ID
   * @returns {Promise<Array>}
   */
  async getAIRecommendations(organizationId) {
    try {
      const response = await api.get('/ai/recommendations', {
        params: { organization_id: organizationId },
      });
      return response.data?.recommendations || [];
    } catch (error) {
      console.error('[HuntApi] Failed to fetch AI recommendations:', error);
      throw error;
    }
  },

  /**
   * Get triage results
   * @param {string} organizationId - Organization ID
   * @param {Object} filters - Query filters
   * @returns {Promise<Array>}
   */
  async getTriageResults(organizationId, filters = {}) {
    try {
      const response = await api.get('/triage/results', {
        params: { organization_id: organizationId, ...filters },
      });
      return response.data?.results || [];
    } catch (error) {
      console.error('[HuntApi] Failed to fetch triage results:', error);
      throw error;
    }
  },

  /**
   * Get triage reasoning for finding
   * @param {string} findingId - Finding ID
   * @returns {Promise<Object>}
   */
  async getTriageReasoning(findingId) {
    try {
      const response = await api.get(`/findings/${findingId}/triage/reasoning`);
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to fetch triage reasoning:', error);
      throw error;
    }
  },

  /**
   * Submit finding to platform
   * @param {string} findingId - Finding ID
   * @param {string} platform - Platform (hackerone, bugcrowd, etc)
   * @param {Object} options - Submission options
   * @returns {Promise<Object>}
   */
  async submitFinding(findingId, platform, options = {}) {
    try {
      const response = await api.post(
        `/findings/${findingId}/submit/${platform}`,
        options
      );
      return response.data;
    } catch (error) {
      console.error('[HuntApi] Failed to submit finding:', error);
      throw error;
    }
  },

  /**
   * Get dashboard metrics
   * @param {string} organizationId - Organization ID
   * @returns {Promise<Object>}
   */
  async getDashboardMetrics(organizationId) {
    try {
      const response = await api.get('/dashboard/metrics', {
        params: { organization_id: organizationId },
      });
      return response.data || {};
    } catch (error) {
      console.error('[HuntApi] Failed to fetch dashboard metrics:', error);
      throw error;
    }
  },
};

export default huntApi;
