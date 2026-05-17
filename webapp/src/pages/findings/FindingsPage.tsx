import React, { useState } from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion, AnimatePresence } from 'framer-motion';

const findingsData = [
  { id: 'VULN-001', title: 'SQL Injection in Login Form', target: 'api.example.com', severity: 'critical', date: '2026-05-15', aiConfidence: 98 },
  { id: 'VULN-002', title: 'Exposed AWS Keys in JS File', target: 'dev.example.com', severity: 'high', date: '2026-05-15', aiConfidence: 95 },
  { id: 'VULN-003', title: 'Stored XSS in User Profile', target: 'app.example.com', severity: 'medium', date: '2026-05-14', aiConfidence: 85 },
  { id: 'VULN-004', title: 'Missing Security Headers', target: 'example.com', severity: 'low', date: '2026-05-14', aiConfidence: 99 },
  { id: 'VULN-005', title: 'Open Directory Listing', target: 'assets.example.com', severity: 'info', date: '2026-05-13', aiConfidence: 92 },
];

const FindingsPage: React.FC = () => {
  const [selectedFinding, setSelectedFinding] = useState<any | null>(null);

  return (
    <div className="space-y-6 relative h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Vulnerability Findings</h1>
          <p className="text-gray-400 text-sm">Review, triage, and export AI-verified vulnerabilities.</p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" className="px-4 py-2">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
            Filters
          </Button>
          <Button variant="primary" className="px-4 py-2">
            Export Report
          </Button>
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 p-0 overflow-hidden">
        <div className="overflow-auto flex-1 custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead className="bg-white/5 border-b border-white/10 sticky top-0 z-10 backdrop-blur-md">
              <tr>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">ID</th>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">Vulnerability</th>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">Target</th>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">Severity</th>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">AI Confidence</th>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">Date</th>
                <th className="py-4 px-6 text-sm font-semibold text-gray-300">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {findingsData.map((finding) => (
                <tr 
                  key={finding.id} 
                  className={`hover:bg-white/5 transition-colors cursor-pointer ${selectedFinding?.id === finding.id ? 'bg-primary/5' : ''}`}
                  onClick={() => setSelectedFinding(finding)}
                >
                  <td className="py-4 px-6 font-mono text-sm text-gray-400">{finding.id}</td>
                  <td className="py-4 px-6 text-sm font-medium text-white">{finding.title}</td>
                  <td className="py-4 px-6 font-mono text-sm text-primary hover:underline">{finding.target}</td>
                  <td className="py-4 px-6">
                    <Badge variant={finding.severity as any} className="uppercase tracking-wider">{finding.severity}</Badge>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-2">
                      <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-secondary rounded-full" style={{ width: `${finding.aiConfidence}%` }}></div>
                      </div>
                      <span className="text-xs text-secondary">{finding.aiConfidence}%</span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-sm text-gray-400">{finding.date}</td>
                  <td className="py-4 px-6">
                    <button className="text-gray-400 hover:text-white transition-colors p-1">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* AI Analysis Drawer */}
      <AnimatePresence>
        {selectedFinding && (
          <motion.div 
            initial={{ opacity: 0, x: 400 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 400 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="absolute top-0 right-0 h-full w-[500px] glass-card border-l border-white/10 shadow-2xl flex flex-col z-20 rounded-l-2xl rounded-r-none"
          >
            <div className="p-6 border-b border-white/10 flex justify-between items-start">
              <div>
                <div className="flex items-center space-x-3 mb-2">
                  <Badge variant={selectedFinding.severity as any} className="uppercase">{selectedFinding.severity}</Badge>
                  <span className="font-mono text-sm text-gray-400">{selectedFinding.id}</span>
                </div>
                <h2 className="text-xl font-bold text-white">{selectedFinding.title}</h2>
              </div>
              <button 
                onClick={() => setSelectedFinding(null)}
                className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-white/10 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="p-6 flex-1 overflow-y-auto custom-scrollbar space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  AI Analysis & Triage
                </h3>
                <div className="bg-secondary/10 border border-secondary/30 rounded-lg p-4 text-sm text-gray-300 leading-relaxed shadow-[0_0_15px_rgba(157,77,255,0.1)]">
                  <p>The AI model confirms this vulnerability with {selectedFinding.aiConfidence}% confidence. The payload <code className="bg-black/30 px-1 py-0.5 rounded text-secondary">' OR '1'='1</code> successfully bypassed authentication on the <code>{selectedFinding.target}</code> endpoint.</p>
                  <p className="mt-2"><strong>Recommendation:</strong> Implement parameterized queries using prepared statements immediately.</p>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Evidence / HTTP Request</h3>
                <div className="bg-[#0B1020] border border-white/10 rounded-lg p-4 overflow-x-auto font-mono text-xs text-gray-400">
                  <pre>
<span className="text-blue-400">POST</span> /api/v1/login <span className="text-purple-400">HTTP/1.1</span><br/>
Host: {selectedFinding.target}<br/>
Content-Type: application/json<br/>
<br/>
{"{"}<br/>
  "username": <span className="text-red-400">"admin' OR '1'='1"</span>,<br/>
  "password": "any"<br/>
{"}"}
                  </pre>
                </div>
              </div>
              
              <div>
                 <h3 className="text-sm font-semibold text-gray-300 mb-2">Markdown Report Preview</h3>
                 <div className="bg-white/5 border border-white/10 rounded-lg p-4 text-sm text-gray-300 prose prose-invert max-w-none">
                    <h4>Description</h4>
                    <p>A SQL Injection vulnerability was discovered...</p>
                 </div>
              </div>
            </div>
            
            <div className="p-6 border-t border-white/10 bg-background-card/80">
              <Button variant="primary" className="w-full">Generate Complete Report</Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FindingsPage;
