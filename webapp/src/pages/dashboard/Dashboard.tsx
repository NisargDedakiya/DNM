import React from 'react';
import { Card, Badge } from '../../components/ui/components';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { motion } from 'framer-motion';

const activityData = [
  { name: '00:00', scans: 400, vulns: 24 },
  { name: '04:00', scans: 300, vulns: 13 },
  { name: '08:00', scans: 550, vulns: 48 },
  { name: '12:00', scans: 450, vulns: 39 },
  { name: '16:00', scans: 700, vulns: 85 },
  { name: '20:00', scans: 600, vulns: 56 },
  { name: '24:00', scans: 400, vulns: 24 },
];

const severityData = [
  { name: 'Critical', count: 12, color: '#FF0055' },
  { name: 'High', count: 45, color: '#FF8A00' },
  { name: 'Medium', count: 120, color: '#FFD600' },
  { name: 'Low', count: 340, color: '#00B8FF' },
  { name: 'Info', count: 850, color: '#9D4DFF' },
];

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Global Operations</h1>
          <p className="text-gray-400">Real-time threat intelligence and recon overview.</p>
        </div>
        <div className="flex items-center space-x-3">
          <Badge variant="primary" className="px-3 py-1 text-sm animate-pulse-glow">
            <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-ping"></span>
            Live Feed Active
          </Badge>
        </div>
      </div>

      {/* Analytics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Active Targets', value: '1,248', trend: '+12%', color: 'primary' },
          { label: 'Open Vulnerabilities', value: '48', trend: '-5%', color: 'critical' },
          { label: 'Recon Scans', value: '8,392', trend: '+24%', color: 'secondary' },
          { label: 'AI Triage Accuracy', value: '98.4%', trend: '+1.2%', color: 'low' },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card glowHover>
              <h3 className="text-sm font-medium text-gray-400 mb-1">{stat.label}</h3>
              <div className="flex items-baseline space-x-2 mb-2">
                <span className="text-3xl font-bold text-white glow-primary">{stat.value}</span>
                <span className={`text-sm font-medium ${stat.trend.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
                  {stat.trend}
                </span>
              </div>
              <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden mt-4">
                <div 
                  className={`h-full rounded-full bg-${stat.color === 'primary' ? 'primary' : stat.color === 'secondary' ? 'secondary' : 'white/20'}`} 
                  style={{ width: '70%' }}
                ></div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <Card className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center">
            <svg className="w-5 h-5 mr-2 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            Recon Activity (24h)
          </h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="colorScans" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00B8FF" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#00B8FF" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.3)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                <YAxis stroke="rgba(255,255,255,0.3)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0B1020', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Area type="monotone" dataKey="scans" stroke="#00B8FF" strokeWidth={2} fillOpacity={1} fill="url(#colorScans)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Severity Overview */}
        <Card>
          <h2 className="text-lg font-semibold text-white mb-6">Severity Breakdown</h2>
          <div className="h-72">
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
                  {
                    severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))
                  }
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Activity Feed */}
        <Card>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-white">Live Activity</h2>
            <button className="text-sm text-primary hover:text-white transition-colors">View All</button>
          </div>
          <div className="space-y-4">
            {[
              { time: 'Just now', event: 'Subfinder discovered 12 new subdomains for target.com', type: 'info' },
              { time: '2m ago', event: 'Nuclei matched CVE-2023-XXXX on staging.target.com', type: 'high' },
              { time: '15m ago', event: 'Port scan completed. 3 new ports opened.', type: 'medium' },
              { time: '1h ago', event: 'Katana finished crawling api.target.com', type: 'info' },
            ].map((feed, i) => (
              <div key={i} className="flex items-start space-x-3 p-3 rounded-lg bg-white/5 border border-white/5 hover:border-white/10 transition-colors">
                <div className="mt-1">
                  {feed.type === 'high' ? (
                    <Badge variant="high">Alert</Badge>
                  ) : feed.type === 'medium' ? (
                    <Badge variant="medium">Warn</Badge>
                  ) : (
                    <Badge variant="info">Info</Badge>
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-200">{feed.event}</p>
                  <p className="text-xs text-gray-500 mt-1">{feed.time}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Scan Queue */}
        <Card>
          <h2 className="text-lg font-semibold text-white mb-6">Scan Queue</h2>
          <div className="space-y-4">
            {[
              { target: 'example.com', tool: 'Nuclei', status: 'Running', progress: 68 },
              { target: 'target.net', tool: 'Katana', status: 'Running', progress: 45 },
              { target: 'internal.corp', tool: 'Naabu', status: 'Pending', progress: 0 },
            ].map((scan, i) => (
              <div key={i} className="p-4 rounded-lg bg-background border border-white/5 relative overflow-hidden">
                <div className="flex justify-between items-center mb-2 relative z-10">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-sm text-white">{scan.target}</span>
                    <span className="text-xs text-gray-500">• {scan.tool}</span>
                  </div>
                  <span className={`text-xs font-semibold ${scan.status === 'Running' ? 'text-primary' : 'text-gray-500'}`}>
                    {scan.status}
                  </span>
                </div>
                <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden relative z-10">
                  <div 
                    className="h-full rounded-full bg-gradient-to-r from-primary to-secondary relative"
                    style={{ width: `${scan.progress}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                  </div>
                </div>
                {scan.status === 'Running' && (
                  <div className="absolute top-0 right-0 w-32 h-full bg-primary/5 blur-xl"></div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
