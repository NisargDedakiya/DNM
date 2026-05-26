import React from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion } from 'framer-motion';

const ReconWorkspace: React.FC = () => {
  const pipelineStages = [
    { name: 'Subfinder', status: 'completed', time: '45s' },
    { name: 'HTTPX', status: 'completed', time: '1m 20s' },
    { name: 'Katana', status: 'running', time: '3m 15s' },
    { name: 'Nuclei', status: 'pending', time: '-' },
    { name: 'AI Triage', status: 'pending', time: '-' },
  ];

  return (
    <div className="space-y-6 h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Recon Workspace</h1>
          <p className="text-gray-400 text-sm">Live pipeline execution and terminal output.</p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" className="px-4 py-2">Pause Pipeline</Button>
          <Button variant="critical" className="bg-[#FF0055]/20 text-[#FF0055] border border-[#FF0055]/30 hover:bg-[#FF0055]/30 px-4 py-2 rounded-lg font-medium transition-colors">
            Halt Scan
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Pipeline & Queue */}
        <div className="xl:col-span-1 space-y-6 flex flex-col">
          <Card className="shrink-0">
            <h2 className="text-lg font-semibold text-white mb-4">Pipeline Status</h2>
            <div className="relative">
              <div className="absolute left-[15px] top-4 bottom-4 w-[2px] bg-white/10"></div>
              <div className="space-y-6">
                {pipelineStages.map((stage, i) => (
                  <div key={stage.name} className="flex items-center relative z-10">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                      stage.status === 'completed' ? 'bg-primary/20 border-primary text-primary shadow-[0_0_10px_rgba(0,184,255,0.5)]' :
                      stage.status === 'running' ? 'bg-secondary/20 border-secondary text-secondary animate-pulse shadow-[0_0_10px_rgba(157,77,255,0.5)]' :
                      'bg-background border-white/20 text-gray-500'
                    }`}>
                      {stage.status === 'completed' ? (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" /></svg>
                      ) : stage.status === 'running' ? (
                        <div className="w-2 h-2 bg-secondary rounded-full"></div>
                      ) : (
                        <span className="text-xs">{i + 1}</span>
                      )}
                    </div>
                    <div className="ml-4 flex-1">
                      <div className="flex justify-between items-center">
                        <span className={`font-medium ${
                          stage.status === 'completed' ? 'text-gray-200' :
                          stage.status === 'running' ? 'text-secondary glow-secondary' :
                          'text-gray-500'
                        }`}>{stage.name}</span>
                        <span className="text-xs text-gray-500 font-mono">{stage.time}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card className="flex-1 min-h-0 flex flex-col">
            <h2 className="text-lg font-semibold text-white mb-4 shrink-0">Active Targets</h2>
            <div className="overflow-y-auto pr-2 space-y-3 flex-1 custom-scrollbar">
              {[
                { target: 'example.com', subdomains: 124, alive: 45 },
                { target: 'api.target.net', subdomains: 12, alive: 12 },
                { target: 'staging.corp', subdomains: 56, alive: 8 },
              ].map((t, i) => (
                <div key={i} className="p-3 bg-white/5 border border-white/10 rounded-lg hover:border-primary/50 transition-colors cursor-pointer group">
                  <div className="font-mono text-sm text-primary mb-2 group-hover:glow-primary">{t.target}</div>
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Subs: <span className="text-white">{t.subdomains}</span></span>
                    <span>Alive: <span className="text-white">{t.alive}</span></span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Live Terminal */}
        <div className="xl:col-span-2 flex flex-col min-h-0">
          <Card className="flex-1 flex flex-col p-0 overflow-hidden bg-background-paper border-white/10 shadow-[0_0_30px_rgba(0,184,255,0.05)]">
            <div className="h-12 border-b border-white/10 bg-background-card/80 flex items-center justify-between px-4 shrink-0">
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                <span className="font-mono text-sm font-medium text-gray-300">Live Operations Terminal</span>
              </div>
              <div className="flex items-center space-x-4">
                <span className="flex items-center text-xs font-mono text-secondary">
                  <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-ping mr-2"></span>
                  WS: CONNECTED
                </span>
                <div className="flex space-x-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                </div>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm text-gray-300 leading-relaxed custom-scrollbar bg-[#050816]">
              <div className="space-y-1">
                <p><span className="text-green-400">root@recon</span>:<span className="text-primary">~</span>$ ./pipeline start --target example.com</p>
                <p className="text-gray-500">[INFO] Initializing distributed recon pipeline v2.4.1</p>
                <p className="text-gray-500">[INFO] Loaded 4,592 nuclei templates</p>
                <br/>
                <p className="text-primary glow-primary">==&gt; Running Subfinder [example.com]</p>
                <p>Found subdomain: api.example.com</p>
                <p>Found subdomain: dev.example.com</p>
                <p>Found subdomain: staging.example.com</p>
                <p>Found subdomain: admin.example.com</p>
                <p className="text-gray-500">[INFO] Subfinder finished. Total: 124 subdomains.</p>
                <br/>
                <p className="text-primary glow-primary">==&gt; Running HTTPX [124 targets]</p>
                <p>api.example.com [200] [application/json] [145ms]</p>
                <p>dev.example.com [403] [text/html] [120ms]</p>
                <p>admin.example.com [401] [text/html] [180ms]</p>
                <p className="text-gray-500">[INFO] HTTPX finished. Alive: 45 hosts.</p>
                <br/>
                <p className="text-secondary glow-secondary">==&gt; Running Katana [45 targets] (In Progress...)</p>
                <p className="opacity-80">Crawling https://api.example.com/v1/</p>
                <p className="opacity-80">Found endpoint: GET /v1/users</p>
                <p className="opacity-80">Found endpoint: POST /v1/auth</p>
                <p className="opacity-80">Crawling https://dev.example.com/</p>
                <p className="opacity-80">Found secret in JS: AKIAIOSFODNN7EXAMPLE</p>
                
                {/* Typing animation cursor */}
                <div className="flex mt-2">
                  <span className="text-green-400">root@recon</span>:<span className="text-primary">~</span>$&nbsp;
                  <div className="w-2 h-4 bg-gray-400 animate-pulse"></div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ReconWorkspace;
