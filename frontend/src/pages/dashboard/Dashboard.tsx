import React from 'react';
import { Card, Badge } from '../../components/ui/components';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';
import { useAuthStore } from '../../stores/authStore';
// @ts-ignore - JSX implementation is intentionally shared across TS and JS entrypoints.
import ExposureTimelineView from '../../timeline/ExposureTimelineView';
// @ts-ignore - JSX implementation is intentionally shared across TS and JS entrypoints.
import InvestigationWorkspace from '../../collaboration/InvestigationWorkspace';
// @ts-ignore - JSX implementation is intentionally shared across TS and JS entrypoints.
import SystemHealthDashboard from '../../monitoring/SystemHealthDashboard';
// @ts-ignore - JSX implementation is intentionally shared across TS and JS entrypoints.
import PerformanceDashboard from '../../performance/PerformanceDashboard';

const severityData = [
  { name: 'Critical', count: 12, color: '#FF0055' },
  { name: 'High', count: 45, color: '#FF8A00' },
  { name: 'Medium', count: 120, color: '#FFD600' },
  { name: 'Low', count: 340, color: '#00B8FF' },
  { name: 'Info', count: 850, color: '#9D4DFF' },
];

const Dashboard: React.FC = () => {
  const organizationId = useAuthStore((state) => state.user?.organization_id || '');
  const highRiskAssets = severityData.filter((entry) => entry.name === 'Critical' || entry.name === 'High');
  const activeHunts = severityData.filter((entry) => entry.name !== 'Info');

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Program Overview</h1>
          <p className="text-gray-400">Total program coverage and vulnerability statistics.</p>
        </div>
        <div className="flex items-center space-x-3">
          <Badge variant="primary" className="px-3 py-1 text-sm animate-pulse-glow">
            <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-ping"></span>
            Sync Active
          </Badge>
        </div>
      </div>

      {/* Program Coverage Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card glowHover>
            <h3 className="text-sm font-medium text-gray-400 mb-1">Total Programs Covered</h3>
            <div className="flex items-baseline space-x-2 mb-2">
              <span className="text-4xl font-bold text-white glow-primary">342</span>
            </div>
            <p className="text-sm text-gray-500">Across all platforms</p>
          </Card>
        </motion.div>
        
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card glowHover>
            <h3 className="text-sm font-medium text-gray-400 mb-1">Total in HackerOne</h3>
            <div className="flex items-baseline space-x-2 mb-2">
              <span className="text-4xl font-bold text-white text-gradient">215</span>
            </div>
            <p className="text-sm text-gray-500">Public & Private Programs</p>
          </Card>
        </motion.div>
        
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card glowHover>
            <h3 className="text-sm font-medium text-gray-400 mb-1">Total in Bugcrowd</h3>
            <div className="flex items-baseline space-x-2 mb-2">
              <span className="text-4xl font-bold text-white text-orange-400">127</span>
            </div>
            <p className="text-sm text-gray-500">Public & Private Programs</p>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vulnerability Finds & Severity */}
        <Card className="flex flex-col">
          <h2 className="text-lg font-semibold text-white mb-2">Vulnerability Finds (By Critical Level)</h2>
          <p className="text-sm text-gray-400 mb-6">Distribution of discovered vulnerabilities.</p>
          
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" stroke="rgba(255,255,255,0.3)" tick={{fontSize: 12}} />
                <YAxis dataKey="name" type="category" stroke="rgba(255,255,255,0.3)" width={70} tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                <Tooltip 
                  cursor={{fill: 'rgba(255,255,255,0.05)'}}
                  contentStyle={{ backgroundColor: '#0B1020', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        
        {/* Recent Vulnerability Info */}
        <Card>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-white">Recent High-Value Finds</h2>
            <button className="text-sm text-primary hover:text-white transition-colors">View All</button>
          </div>
          <div className="space-y-4">
            {[
              { id: 'VULN-092', target: 'api.uber.com', type: 'SQL Injection', severity: 'Critical', bounty: '$5,000' },
              { id: 'VULN-091', target: 'admin.shopify.com', type: 'Authentication Bypass', severity: 'High', bounty: '$2,500' },
              { id: 'VULN-090', target: 'internal.yahoo.com', type: 'SSRF', severity: 'High', bounty: '$1,500' },
              { id: 'VULN-089', target: 'app.example.com', type: 'Stored XSS', severity: 'Medium', bounty: '$500' },
            ].map((vuln) => (
              <div key={vuln.id} className="p-4 rounded-lg bg-white/5 border border-white/5 hover:border-white/10 transition-colors flex justify-between items-center">
                <div>
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="font-bold text-white text-sm">{vuln.type}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase
                      ${vuln.severity === 'Critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 
                        vuln.severity === 'High' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' : 
                        'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'}`}>
                      {vuln.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 font-mono">{vuln.target}</p>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-green-400">{vuln.bounty}</div>
                  <div className="text-[10px] text-gray-500">Est. Bounty</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {organizationId && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <ExposureTimelineView organizationId={organizationId} />
        </motion.div>
      )}

      {organizationId && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
        >
          <InvestigationWorkspace
            organizationId={organizationId}
            attackGraphSummary={{
              nodes: highRiskAssets.length,
              edges: activeHunts.length,
              summary: 'Correlate P1/P2 findings, evidence, and assignment ownership within a single org-isolated workspace.',
            }}
          />
        </motion.div>
      )}

      {organizationId && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.52 }}
          className="mt-6"
        >
          <PerformanceDashboard organizationId={organizationId} />
        </motion.div>
      )}

      {organizationId && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-6"
        >
          <SystemHealthDashboard organizationId={organizationId} />
        </motion.div>
      )}
    </div>
  );
};

export default Dashboard;
