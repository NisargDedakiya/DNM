import React, { useState } from 'react'

const SSOConfiguration = ({ initialValue = null, onSave = null }) => {
  const [providerType, setProviderType] = useState(initialValue?.provider_type || 'saml')
  const [metadata, setMetadata] = useState(JSON.stringify(initialValue?.provider_metadata || { issuer: '', entrypoint: '', client_id: '' }, null, 2))
  const [enabled, setEnabled] = useState(initialValue?.enabled ?? true)

  const handleSave = (event) => {
    event.preventDefault()
    onSave?.({ provider_type: providerType, provider_metadata: JSON.parse(metadata), enabled })
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5 text-white">
      <h3 className="text-lg font-semibold">SSO configuration</h3>
      <p className="mt-1 text-sm text-slate-400">Manage SAML metadata and OAuth provider details for enterprise federation.</p>

      <form className="mt-4 space-y-4" onSubmit={handleSave}>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-300">Provider type</span>
          <select value={providerType} onChange={(event) => setProviderType(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 outline-none">
            <option value="saml">SAML</option>
            <option value="google_workspace">Google Workspace</option>
            <option value="microsoft_entra_id">Microsoft Entra ID</option>
            <option value="okta">Okta</option>
            <option value="github_enterprise">GitHub Enterprise</option>
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-slate-300">Provider metadata</span>
          <textarea value={metadata} onChange={(event) => setMetadata(event.target.value)} rows={8} className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 font-mono text-xs outline-none" />
        </label>

        <label className="flex items-center gap-3 text-sm text-slate-300">
          <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
          Enabled for the organization
        </label>

        <button type="submit" className="rounded-2xl bg-cyan-500 px-4 py-3 font-semibold text-slate-950">Save provider</button>
      </form>
    </section>
  )
}

export default SSOConfiguration
