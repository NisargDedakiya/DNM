import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/components';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-white selection:bg-primary/30 overflow-hidden relative">
      {/* Background Effects */}
      <div className="fixed inset-0 z-0 opacity-10 pointer-events-none" 
           style={{ backgroundImage: 'linear-gradient(#00B8FF 1px, transparent 1px), linear-gradient(90deg, #00B8FF 1px, transparent 1px)', backgroundSize: '40px 40px', transform: 'perspective(500px) rotateX(60deg) scale(2)', transformOrigin: 'top center' }}>
      </div>
      <div className="fixed top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-primary/20 blur-[150px] pointer-events-none z-0"></div>
      <div className="fixed bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-secondary/20 blur-[150px] pointer-events-none z-0"></div>

      {/* Navbar */}
      <nav className="relative z-20 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center space-x-3">
          <img src="/logo.svg" alt="DNM Logo" className="h-10 w-auto" />
          <span className="font-bold text-xl tracking-wider text-gradient">NisargHunter</span>
        </div>
        <div className="hidden md:flex items-center space-x-8 text-sm font-medium text-gray-300">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#platform" className="hover:text-white transition-colors">Platform</a>
          <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
        </div>
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={() => navigate('/login')}>Login</Button>
          <Button variant="primary" onClick={() => navigate('/login')}>Get Started</Button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex flex-col items-center justify-center min-h-[80vh] px-4 text-center max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="inline-flex items-center px-4 py-2 rounded-full glass-panel mb-8 border border-primary/30"
        >
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse mr-3"></span>
          <span className="text-sm font-medium text-primary">Next-Gen Recon Intelligence is Live</span>
        </motion.div>

        <motion.h1 
          className="text-5xl md:text-7xl font-bold mb-6 leading-tight tracking-tight"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          AI-Powered Bug Bounty <br />
          <span className="text-gradient glow-primary">Intelligence Platform</span>
        </motion.h1>

        <motion.p 
          className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          Automate your recon workflow, prioritize critical vulnerabilities with AI, and dominate the bug bounty landscape with an elite operator workstation.
        </motion.p>

        <motion.div 
          className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          <Button variant="primary" className="px-8 py-4 text-lg" onClick={() => navigate('/login')}>
            Start Scanning
            <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </Button>
          <Button variant="outline" className="px-8 py-4 text-lg bg-background-card/50 backdrop-blur-md">
            View Documentation
          </Button>
        </motion.div>

        {/* Dashboard Preview Mockup */}
        <motion.div 
          className="mt-20 w-full max-w-6xl relative"
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.8 }}
        >
          <div className="absolute -inset-1 bg-gradient-to-r from-primary to-secondary rounded-2xl blur-lg opacity-30"></div>
          <div className="relative rounded-xl overflow-hidden glass-panel border border-white/10 shadow-2xl">
            <div className="h-8 bg-background-card/80 border-b border-white/10 flex items-center px-4 space-x-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
            </div>
            <div className="bg-background-paper p-1 flex">
               <div className="w-1/4 border-r border-white/5 p-4 space-y-3 opacity-50">
                  <div className="h-4 w-1/2 bg-white/10 rounded"></div>
                  <div className="h-4 w-3/4 bg-white/5 rounded"></div>
                  <div className="h-4 w-2/3 bg-white/5 rounded"></div>
               </div>
               <div className="w-3/4 p-6">
                  <div className="flex space-x-4 mb-6">
                    <div className="flex-1 h-24 rounded-lg border border-white/10 bg-white/5 flex flex-col justify-center px-4 relative overflow-hidden">
                       <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-transparent"></div>
                       <div className="h-3 w-1/3 bg-primary/40 rounded mb-2"></div>
                       <div className="h-6 w-1/2 bg-white/80 rounded"></div>
                    </div>
                    <div className="flex-1 h-24 rounded-lg border border-white/10 bg-white/5 flex flex-col justify-center px-4 relative overflow-hidden">
                       <div className="absolute inset-0 bg-gradient-to-r from-secondary/10 to-transparent"></div>
                       <div className="h-3 w-1/3 bg-secondary/40 rounded mb-2"></div>
                       <div className="h-6 w-1/2 bg-white/80 rounded"></div>
                    </div>
                  </div>
                  <div className="h-48 rounded-lg border border-white/10 bg-white/5 flex items-end p-4 space-x-2 opacity-70">
                    {[40, 70, 45, 90, 65, 80, 50, 100].map((h, i) => (
                      <div key={i} className="flex-1 rounded-t-sm bg-gradient-to-t from-primary/20 to-primary/60" style={{ height: `${h}%` }}></div>
                    ))}
                  </div>
               </div>
            </div>
          </div>
        </motion.div>
      </main>

      {/* Terminal Live Activity */}
      <section className="relative z-10 py-24 px-4 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Elite Operator Workspace</h2>
          <p className="text-gray-400 max-w-2xl mx-auto">Experience a terminal-driven UI blended with modern analytics.</p>
        </div>
        
        <div className="glass-card overflow-hidden border border-white/10">
          <div className="bg-background-card/90 border-b border-white/10 px-4 py-2 flex items-center justify-between">
             <span className="font-mono text-xs text-gray-400">recon-terminal ~ /operations</span>
             <span className="flex space-x-2">
                <span className="w-2 h-2 rounded-full bg-primary/80 animate-pulse"></span>
             </span>
          </div>
          <div className="p-6 font-mono text-sm leading-relaxed text-gray-300 h-64 overflow-hidden relative">
            <div className="space-y-2 opacity-80">
              <p><span className="text-primary">➜</span> <span className="text-white">nisarg-ai</span> start recon --target example.com</p>
              <p className="text-gray-500">[10:04:22] [INF] Starting pipeline for example.com</p>
              <p className="text-gray-500">[10:04:25] [INF] Subfinder found 1,245 subdomains</p>
              <p className="text-gray-500">[10:04:40] [INF] Resolving hosts with httpx...</p>
              <p><span className="text-secondary">[AI]</span> Analyzing attack surface graph...</p>
              <p className="text-green-400">[10:05:12] [SUCCESS] Identified 3 high-value targets</p>
              <p><span className="text-primary">➜</span> <span className="text-white">nisarg-ai</span> run nuclei --critical</p>
              <div className="flex space-x-1 mt-2">
                <div className="w-2 h-4 bg-primary animate-pulse"></div>
              </div>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-24 bg-gradient-to-t from-background-card/80 to-transparent"></div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 py-12 text-center text-gray-500">
        <div className="flex items-center justify-center space-x-3 mb-6 opacity-50">
          <img src="/logo.svg" alt="DNM Logo" className="h-6 w-auto grayscale" />
          <span className="font-bold tracking-wider">NisargHunter</span>
        </div>
        <p>© 2026 NisargHunter AI. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;
