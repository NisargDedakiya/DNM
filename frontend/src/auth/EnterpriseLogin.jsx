import React, { useState } from 'react'
import api from '../api/client'
import useAuthStore from '../stores/authStore'

const providers = [
  { value: 'saml', label: 'SAML SSO' },
  { value: 'google_workspace', label: 'Google Workspace' },
  { value: 'microsoft_entra_id', label: 'Microsoft Entra ID' },
  { value: 'okta', label: 'Okta' },
  { value: 'github_enterprise', label: 'GitHub Enterprise' },
]

const EnterpriseLogin = ({ onSuccess = null }) => {
  const setToken = useAuthStore((state) => state.setToken)
  const setUser = useAuthStore((state) => state.setUser)
  const [organizationId, setOrganizationId] = useState('')
  const [provider, setProvider] = useState('saml')
  const [subject, setSubject] = useState('')
  const [secret, setSecret] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const endpoint = provider === 'saml' ? '/sso/saml' : '/sso/oauth'
      const payload = provider === 'saml'
        ? { organization_id: organizationId, saml_response: subject, audience: 'nisarghunter' }
        : { organization_id: organizationId, provider, access_token: secret, workspace_id: null }
      const response = await api.post(endpoint, payload)
      if (response.data?.access_token) setToken(response.data.access_token)
      if (response.data?.identity) {
        setUser({
          id: response.data.identity.user_id || response.data.identity.external_identity || 'enterprise-user',
          username: response.data.identity.username || response.data.identity.external_identity || 'enterprise-user',
          email: response.data.identity.email,
          organization_id: response.data.organization_id,
          role: response.data.identity.role || response.data.identity.federated_role,
        })
      }
      onSuccess?.(response.data)
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Enterprise authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-white shadow-[0_24px_90px_rgba(0,0,0,0.34)]">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">Enterprise SSO</p>
        <h2 className="mt-2 text-2xl font-semibold">Private login for confidential operations</h2>
        <p className="mt-2 text-sm text-slate-300">Authenticate with SAML or federated OAuth while preserving org isolation and auditability.</p>
      </div>

      {error ? <div className="mb-4 rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}

      <form className="space-y-4" onSubmit={handleLogin}>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-300">Organization ID</span>
          <input value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 outline-none focus:border-cyan-400/50" placeholder="org_..." />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-300">Provider</span>
          <select value={provider} onChange={(event) => setProvider(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 outline-none focus:border-cyan-400/50">
            {providers.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>

        {provider === 'saml' ? (
          <label className="block text-sm">
            <span className="mb-1 block text-slate-300">SAML response</span>
            <textarea value={subject} onChange={(event) => setSubject(event.target.value)} rows={5} className="w-full rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 outline-none focus:border-cyan-400/50" placeholder="Base64 SAML assertion" />
          </label>
        ) : (
          <label className="block text-sm">
            <span className="mb-1 block text-slate-300">Access token</span>
            <input value={secret} onChange={(event) => setSecret(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 outline-none focus:border-cyan-400/50" placeholder="Provider token" />
          </label>
        )}

        <button type="submit" disabled={loading} className="w-full rounded-2xl bg-cyan-500 px-4 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60">
          {loading ? 'Authenticating...' : 'Initiate Enterprise Session'}
        </button>
      </form>
    </section>
  )
}

export default EnterpriseLogin
