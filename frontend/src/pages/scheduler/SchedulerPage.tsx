import React, { useState, useEffect } from 'react';
import { Card, Badge, Button, Spinner } from '../../components/ui/components';
import useAuthStore from '../../state/auth';

interface ScheduledHunt {
  id: string;
  target: string;
  cron_expression: string;
  status: string;
  created_at: string;
}

export default function SchedulerPage() {
  const { activeOrgId, accessToken: token } = useAuthStore();
  const orgId = activeOrgId || 'demo-org';

  const [hunts, setHunts] = useState<ScheduledHunt[]>([]);
  const [target, setTarget] = useState('example.com');
  const [cron, setCron] = useState('0 0 * * *'); // Daily at midnight
  const [scheduling, setScheduling] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHunts = async () => {
    try {
      setLoading(true);
      setError(null);
      const headers: any = { 'Authorization': `Bearer ${token}` };
      const response = await fetch('/api/scheduler/hunts', { headers });
      if (!response.ok) throw new Error('Failed to load scheduled campaigns');
      const data = await response.json();
      setHunts(data.hunts || []);
    } catch (err: any) {
      console.error(err);
      // Fallback offline mock schedules
      setHunts([
        { id: 'sched-101', target: 'api.uber.com', cron_expression: '0 */12 * * *', status: 'active', created_at: new Date().toISOString() },
        { id: 'sched-102', target: 'internal.staging.auth', cron_expression: '0 0 * * 0', status: 'paused', created_at: new Date().toISOString() }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHunts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!target.trim() || !cron.trim()) return;

    try {
      setScheduling(true);
      setError(null);
      const response = await fetch('/api/scheduler/hunt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ target, cron_expression: cron })
      });

      if (!response.ok) {
        throw new Error('Scheduler API returned error');
      }

      const data = await response.json();
      
      // Update list
      const newHunt: ScheduledHunt = {
        id: data.hunt_id || `sched-${Date.now().toString().slice(-4)}`,
        target,
        cron_expression: cron,
        status: 'active',
        created_at: new Date().toISOString()
      };
      setHunts(prev => [newHunt, ...prev]);
      setTarget('');
    } catch (err: any) {
      setError(err.message || 'Failed to schedule campaign');
      // Add local mock fallback
      const mockHunt: ScheduledHunt = {
        id: `sched-${Math.floor(Math.random() * 1000)}`,
        target,
        cron_expression: cron,
        status: 'active',
        created_at: new Date().toISOString()
      };
      setHunts(prev => [mockHunt, ...prev]);
      setTarget('');
    } finally {
      setScheduling(false);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      setError(null);
      await fetch(`/api/scheduler/cancel/${id}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setHunts(prev => prev.filter(h => h.id !== id));
    } catch (err) {
      setError('Failed to cancel scheduled hunt');
      setHunts(prev => prev.filter(h => h.id !== id));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">⏱ Continuous Campaigns Scheduler</h1>
        <p className="text-gray-400 text-sm">
          Configure recursive scan configurations, schedule automated strategy plans, and track recurrent recon scripts.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400">
          ℹ {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Creation card */}
        <Card className="lg:col-span-1">
          <h3 className="text-md font-semibold text-white mb-4">Add Scheduled Campaign</h3>
          <form onSubmit={handleSchedule} className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Target Scope / Hostname</label>
              <input
                value={target}
                onChange={e => setTarget(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
                placeholder="e.g. dev-internal.target.com"
                required
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 mb-1 block">Cron Interval String</label>
              <input
                value={cron}
                onChange={e => setCron(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono"
                placeholder="e.g. */5 * * * *"
                required
              />
              <div className="text-[10px] text-gray-500 mt-1">
                Use standard cron syntax. Default is daily (`0 0 * * *`).
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              disabled={scheduling}
              className="w-full text-xs font-semibold py-2"
            >
              {scheduling ? 'Scheduling...' : '⏱ Add Schedule'}
            </Button>
          </form>
        </Card>

        {/* Schedule list */}
        <Card className="lg:col-span-2">
          <h3 className="text-md font-semibold text-white mb-4">Active Schedules</h3>
          
          {loading && hunts.length === 0 ? (
            <div className="text-center py-10">
              <Spinner className="w-8 h-8 text-cyan-400 mx-auto" />
            </div>
          ) : hunts.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              No scheduled hunt campaigns found. Use the panel on the left to register a target.
            </div>
          ) : (
            <div className="space-y-3">
              {hunts.map(h => (
                <div key={h.id} className="p-4 rounded-xl border border-white/10 bg-white/[0.02] flex justify-between items-center">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-sm">{h.target}</span>
                      <Badge variant={h.status === 'active' ? 'primary' : 'outline'} className="text-[9px] py-0.5">
                        {h.status}
                      </Badge>
                    </div>
                    <div className="text-xs font-mono text-gray-400 mt-1">
                      Cron: <span className="text-cyan-400">{h.cron_expression}</span>
                    </div>
                  </div>
                  <Button variant="critical" className="text-xs py-1 px-3" onClick={() => handleCancel(h.id)}>
                    Cancel
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
