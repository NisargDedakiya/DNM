import React from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion } from 'framer-motion';

const AssetsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Asset Intelligence</h1>
          <p className="text-gray-400 text-sm">Visualize attack surface, endpoints, and technology stacks.</p>
        </div>
        <div className="flex space-x-3">
          <Button variant="outline" className="px-4 py-2">Sync Assets</Button>
          <Button variant="primary" className="px-4 py-2">Add Seed</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Asset Graph Placeholder */}
        <Card className="xl:col-span-3 min-h-[500px] flex flex-col relative overflow-hidden">
          <div className="flex justify-between items-center mb-4 z-10 relative">
             <h2 className="text-lg font-semibold text-white">Attack Surface Graph</h2>
             <div className="flex space-x-2">
               <Badge variant="primary">Force Directed</Badge>
               <Badge variant="outline" className="border-white/10 text-gray-400">Hierarchical</Badge>
             </div>
          </div>
          
          <div className="flex-1 rounded-lg border border-white/5 bg-[#050816] relative flex items-center justify-center overflow-hidden">
             {/* Mock Graph Nodes */}
             <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at center, #00B8FF 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
             
             <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 4, repeat: Infinity }} className="absolute z-10 flex flex-col items-center">
                <div className="w-16 h-16 rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center shadow-[0_0_30px_rgba(0,184,255,0.4)]">
                   <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>
                </div>
                <span className="mt-2 font-mono text-sm text-white bg-background/80 px-2 py-1 rounded">example.com</span>
             </motion.div>

             {/* Connection Lines (Mock) */}
             <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-50">
               <path d="M 50% 50% L 30% 30%" stroke="#00B8FF" strokeWidth="2" strokeDasharray="5,5" />
               <path d="M 50% 50% L 70% 30%" stroke="#9D4DFF" strokeWidth="2" />
               <path d="M 50% 50% L 30% 70%" stroke="#00B8FF" strokeWidth="2" />
               <path d="M 50% 50% L 70% 70%" stroke="#FF8A00" strokeWidth="2" strokeDasharray="5,5" />
             </svg>

             {/* Child Nodes */}
             <motion.div animate={{ y: [0, 10, 0] }} transition={{ duration: 3, repeat: Infinity, delay: 0.5 }} className="absolute top-[25%] left-[25%] flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur-sm">
                  <span className="text-xs font-bold text-white">API</span>
                </div>
                <span className="mt-1 font-mono text-xs text-gray-400">api.example.com</span>
             </motion.div>

             <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 5, repeat: Infinity, delay: 1 }} className="absolute top-[25%] right-[25%] flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-secondary/20 border border-secondary flex items-center justify-center shadow-[0_0_15px_rgba(157,77,255,0.4)] backdrop-blur-sm">
                  <span className="text-xs font-bold text-secondary">DEV</span>
                </div>
                <span className="mt-1 font-mono text-xs text-secondary glow-secondary">dev.example.com</span>
             </motion.div>

             <motion.div animate={{ y: [0, 5, 0] }} transition={{ duration: 3.5, repeat: Infinity, delay: 1.5 }} className="absolute bottom-[25%] left-[25%] flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur-sm">
                  <span className="text-xs font-bold text-white">WWW</span>
                </div>
                <span className="mt-1 font-mono text-xs text-gray-400">www.example.com</span>
             </motion.div>

             <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 4.5, repeat: Infinity, delay: 2 }} className="absolute bottom-[25%] right-[25%] flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-[#FF8A00]/20 border border-[#FF8A00] flex items-center justify-center shadow-[0_0_15px_rgba(255,138,0,0.4)] backdrop-blur-sm">
                  <span className="text-xs font-bold text-[#FF8A00]">STG</span>
                </div>
                <span className="mt-1 font-mono text-xs text-[#FF8A00]">staging.example.com</span>
             </motion.div>
          </div>
        </Card>

        <div className="xl:col-span-1 space-y-6">
          {/* Technology Fingerprints */}
          <Card>
            <h2 className="text-lg font-semibold text-white mb-4">Tech Stack</h2>
            <div className="space-y-3">
               {[
                 { name: 'Nginx', version: '1.18.0', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
                 { name: 'React', version: '17.0.2', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
                 { name: 'Express', version: '4.17.1', color: 'bg-gray-500/20 text-gray-300 border-gray-500/30' },
                 { name: 'PostgreSQL', version: '13.3', color: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' },
               ].map(tech => (
                 <div key={tech.name} className="flex justify-between items-center p-2 rounded bg-white/5 border border-white/5">
                   <span className="text-sm text-white">{tech.name}</span>
                   <span className={`text-xs px-2 py-0.5 rounded-full border ${tech.color}`}>{tech.version}</span>
                 </div>
               ))}
            </div>
          </Card>

          {/* Exposure Tracking */}
          <Card>
            <h2 className="text-lg font-semibold text-white mb-4">Open Ports</h2>
            <div className="flex flex-wrap gap-2">
               {['80 HTTP', '443 HTTPS', '22 SSH', '5432 PG', '8080 ALT'].map(port => (
                 <Badge key={port} variant="outline" className="font-mono">{port}</Badge>
               ))}
               <Badge variant="critical" className="animate-pulse font-mono">21 FTP</Badge>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AssetsPage;
