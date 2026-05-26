import React from 'react';

const codeSamples = [
  {
    title: 'Python SDK',
    code: `from backend.sdk.python_sdk import authenticate\n\nclient = authenticate('https://api.example.com', api_key='pk_live_xxx')\nfindings = client.get_findings('org-uuid')`,
  },
  {
    title: 'JavaScript SDK',
    code: `import { authenticate } from './backend/sdk/javascript_sdk.js'\n\nconst client = authenticate('https://api.example.com', 'pk_live_xxx')\nconst findings = await client.fetchFindings('org-uuid')`,
  },
  {
    title: 'GraphQL',
    code: `query DeveloperView($organizationId: ID!) {\n  attackPaths(organizationId: $organizationId, depth: 2) {\n    nodes { id type }\n    edges { source target severity }\n  }\n}`,
  },
  {
    title: 'Webhook',
    code: `POST /developer/webhook\nX-API-Key: pk_live_xxx\n{\n  "organization_id": "org-uuid",\n  "endpoint": "https://hooks.example.com/nisarghunter",\n  "subscribed_events": ["finding.p1_alert", "attack-path.escalation"]\n}`,
  },
];

export default function APIDocumentation() {
  return (
    <div className="space-y-6 rounded-3xl border border-white/10 bg-slate-950/80 p-6 text-slate-100 shadow-2xl shadow-cyan-950/20">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-cyan-300/80">Documentation</p>
        <h3 className="text-2xl font-semibold text-white">Public APIs, SDKs, GraphQL, and webhooks</h3>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {codeSamples.map((sample) => (
          <article key={sample.title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <h4 className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300/80">{sample.title}</h4>
            <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-900/90 p-4 text-xs text-slate-300">
              <code>{sample.code}</code>
            </pre>
          </article>
        ))}
      </div>
    </div>
  );
}
