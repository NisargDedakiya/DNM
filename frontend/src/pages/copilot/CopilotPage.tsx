import React, { useState } from 'react';
import { Card, Badge, Button } from '../../components/ui/components';
import { motion } from 'framer-motion';
import { getCopilotChat, investigateEntity } from '../../api/clients/copilot';
import useAuthStore from '../../state/auth';

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const CopilotPage: React.FC = () => {
  const { user, activeOrgId } = useAuthStore();
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !activeOrgId) return;

    try {
      setLoading(true);
      setError(null);

      // Add user message
      const userMsg: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: query,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMsg]);
      setQuery('');

      // Get copilot response
      const response = await getCopilotChat(user.organization_id, query);
      
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response?.response || response?.message || 'No response',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to process query');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div>
        <h1 className="text-2xl font-bold text-white mb-1">AI Security Copilot</h1>
        <p className="text-gray-400 text-sm">Ask questions about your assets, exposures, and findings</p>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400 flex items-center space-x-2">
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </motion.div>
      )}

      {/* Chat History */}
      <Card className="flex-1 overflow-y-auto max-h-96">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <svg className="w-12 h-12 text-gray-600 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-gray-500 text-sm">Start a conversation with the AI copilot</p>
              <p className="text-gray-600 text-xs mt-2">Ask about security findings, asset risks, or investigation insights</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs px-4 py-2 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-primary/30 text-white rounded-br-none'
                      : 'bg-white/5 text-gray-300 rounded-bl-none'
                  }`}
                >
                  <p className="text-sm">{msg.content}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </Card>

      {/* Input Form */}
      <form onSubmit={handleQuery} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Ask a security question..."
          disabled={loading}
          className="flex-1 bg-background-card/50 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
        />
        <Button
          type="submit"
          variant="primary"
          disabled={loading || !query.trim()}
          className="shrink-0"
        >
          {loading ? '...' : 'Send'}
        </Button>
      </form>

      <div className="text-xs text-gray-500 text-center">
        <Badge variant="outline" className="text-xs">AI analysis is advisory only</Badge>
      </div>
    </div>
  );
};

export default CopilotPage;
