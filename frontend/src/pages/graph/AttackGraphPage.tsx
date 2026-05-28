import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Card, Badge, Button, Spinner } from '../../components/ui/components';
import { motion, AnimatePresence } from 'framer-motion';
import useAuthStore from '../../state/auth';
import { getIntelMap, traverseNode, getRiskPropagation } from '../../api/clients/graph';
import AttackPathVisualizer from '../../attack/AttackPathVisualizer';
import BlastRadiusPanel from '../../attack/BlastRadiusPanel';
import LateralMovementView from '../../attack/LateralMovementView';
import PrivilegeChainExplorer from '../../attack/PrivilegeChainExplorer';

interface Node {
  id: string;
  label: string;
  type: string;
  reference_id: string;
  metadata?: any;
  x?: number;
  y?: number;
}

interface Edge {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence?: number;
  weight?: number;
  notes?: string;
}

export default function AttackGraphPage() {
  const { user, activeOrgId, accessToken: token } = useAuthStore();
  const orgId = activeOrgId || 'demo-org';

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [surface, setSurface] = useState<any>(null);
  const [clusters, setClusters] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interaction states
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [traversalDepth, setTraversalDepth] = useState(3);
  const [traversalDirection, setTraversalDirection] = useState<'outgoing' | 'incoming' | 'both'>('outgoing');
  const [traversing, setTraversing] = useState(false);
  const [simulatingRisk, setSimulatingRisk] = useState(false);
  
  // Simulation outcome states
  const [riskPropagationData, setRiskPropagationData] = useState<any>(null);
  const [affectedNodeIds, setAffectedNodeIds] = useState<Record<string, number>>({});
  
  // Layout states
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const [graphTab, setGraphTab] = useState<'blast' | 'lateral' | 'privilege' | 'reasoning'>('reasoning');

  // Fetch full topology intelligence map
  const fetchGraph = async () => {
    if (!orgId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getIntelMap(orgId);
      
      const rawNodes = data.nodes || [];
      const rawEdges = data.edges || [];

      // Apply organic physics-like relaxation layout
      const initializedNodes = rawNodes.map((n: any, idx: number) => ({
        ...n,
        x: 400 + Math.cos(idx) * 250 + (Math.random() - 0.5) * 50,
        y: 250 + Math.sin(idx) * 180 + (Math.random() - 0.5) * 50,
      }));

      // Run force-directed layout computation
      for (let k = 0; k < 120; k++) {
        // Repulse all nodes from each other
        for (let i = 0; i < initializedNodes.length; i++) {
          for (let j = i + 1; j < initializedNodes.length; j++) {
            const dx = initializedNodes[j].x - initializedNodes[i].x;
            const dy = initializedNodes[j].y - initializedNodes[i].y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const minDist = 110;
            if (dist < minDist) {
              const force = (minDist - dist) * 0.18;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;
              initializedNodes[j].x += fx;
              initializedNodes[j].y += fy;
              initializedNodes[i].x -= fx;
              initializedNodes[i].y -= fy;
            }
          }
        }

        // Attract connected nodes along edges
        rawEdges.forEach((edge: any) => {
          const sNode = initializedNodes.find((n: any) => n.id === edge.source);
          const tNode = initializedNodes.find((n: any) => n.id === edge.target);
          if (sNode && tNode) {
            const dx = tNode.x - sNode.x;
            const dy = tNode.y - sNode.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const desiredDist = 140;
            const force = (dist - desiredDist) * 0.05;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            tNode.x -= fx;
            tNode.y -= fy;
            sNode.x += fx;
            sNode.y += fy;
          }
        });

        // Pull slightly to center to avoid floating away
        initializedNodes.forEach((node: any) => {
          const dx = 400 - node.x;
          const dy = 250 - node.y;
          node.x += dx * 0.01;
          node.y += dy * 0.01;
        });
      }

      // Constrain inside viewport boundaries
      initializedNodes.forEach((node: any) => {
        node.x = Math.max(50, Math.min(750, node.x));
        node.y = Math.max(50, Math.min(450, node.y));
      });

      setNodes(initializedNodes);
      setEdges(rawEdges);
      setStats(data.stats || null);
      setSurface(data.surface_analysis || null);
      setClusters(data.risk_summary || null);
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || 'Failed to sync intelligence graph');
      
      // Fallback offline mock data for high-signal preview
      loadMockGraph();
    } finally {
      setLoading(false);
    }
  };

  const loadMockGraph = () => {
    const mockNodes = [
      { id: '1', label: 'AWS SSO Portal', type: 'exposure', reference_id: 'ref-1', metadata: { severity: 'critical', risk_score: 9.5 } },
      { id: '2', label: 'production-db-01', type: 'asset', reference_id: 'ref-2', metadata: { severity: 'high', risk_score: 8.4, hostname: 'prod-db.internal' } },
      { id: '3', label: 'Legacy Image Parser', type: 'finding', reference_id: 'ref-3', metadata: { severity: 'critical', risk_score: 9.0, summary: 'SSRF vulnerability' } },
      { id: '4', label: 'api.nisarghunter.ai', type: 'asset', reference_id: 'ref-4', metadata: { severity: 'medium', risk_score: 6.2, hostname: 'api.nisarghunter.ai' } },
      { id: '5', label: 'Developer Laptop', type: 'asset', reference_id: 'ref-5', metadata: { severity: 'low', risk_score: 3.5 } },
    ];

    const mockEdges = [
      { id: 'e1', source: '1', target: '2', type: 'access' },
      { id: 'e2', source: '3', target: '4', type: 'exploits' },
      { id: 'e3', source: '4', target: '2', type: 'lateral_movement' },
      { id: 'e4', source: '5', target: '1', type: 'authenticates' },
    ];

    const positioned = mockNodes.map((n, i) => ({
      ...n,
      x: 200 + i * 110 + (Math.random() - 0.5) * 40,
      y: 150 + (i % 2 === 0 ? 150 : 80),
    }));

    setNodes(positioned);
    setEdges(mockEdges);
    setStats({ total_nodes: 5, total_edges: 4, total_findings: 1 });
    setSurface({ connectivity_score: 72, entry_points: [], exposure_density: [], technology_spread: [] });
  };

  useEffect(() => {
    fetchGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  // Handle graph SVG interactions
  const handleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    setDraggedNodeId(nodeId);
    const node = nodes.find(n => n.id === nodeId);
    if (node) setSelectedNode(node);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggedNodeId || !svgRef.current) return;
    
    const rect = svgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setNodes(prev =>
      prev.map(n => (n.id === draggedNodeId ? { ...n, x: Math.max(20, Math.min(rect.width - 20, x)), y: Math.max(20, Math.min(rect.height - 20, y)) } : n))
    );
  };

  const handleMouseUp = () => {
    setDraggedNodeId(null);
  };

  // Traversal logic
  const handleTraverse = async () => {
    if (!selectedNode || !orgId) return;
    try {
      setTraversing(true);
      setError(null);
      const data = await traverseNode(selectedNode.id, orgId, {
        max_depth: traversalDepth,
        direction: traversalDirection,
      });

      // Filter and position traversal nodes
      const traversedNodes = Object.values(data.nodes || {}).map((n: any, idx: number) => ({
        id: String(n.id),
        label: n.label,
        type: n.node_type || 'asset',
        reference_id: String(n.reference_id),
        metadata: n.metadata || {},
        x: 400 + Math.cos(idx) * 200,
        y: 250 + Math.sin(idx) * 150,
      }));

      const traversedEdges = (data.edges || []).map((e: any) => ({
        id: String(e.id),
        source: String(e.source_node_id),
        target: String(e.target_node_id),
        type: e.relationship_type,
      }));

      setNodes(traversedNodes);
      setEdges(traversedEdges);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to traverse node neighbourhood');
    } finally {
      setTraversing(false);
    }
  };

  // Risk propagation simulation
  const handleSimulateRisk = async () => {
    if (!selectedNode || !orgId) return;
    try {
      setSimulatingRisk(true);
      setRiskPropagationData(null);
      setAffectedNodeIds({});
      
      const response = await getRiskPropagation(selectedNode.id, orgId, traversalDepth);
      setRiskPropagationData(response);
      
      const risks: Record<string, number> = {};
      Object.keys(response.propagated_risks || {}).forEach((nodeId) => {
        risks[nodeId] = response.propagated_risks[nodeId].propagated_risk;
      });
      setAffectedNodeIds(risks);
    } catch (err: any) {
      console.error(err);
      setError('Risk simulation endpoint failed. Displaying simulated threat propagation path.');
      
      // Fallback local simulation mapping
      const localSim: Record<string, number> = {};
      edges.forEach(e => {
        if (e.source === selectedNode.id) {
          localSim[e.target] = 8.5;
          edges.forEach(e2 => {
            if (e2.source === e.target) localSim[e2.target] = 5.2;
          });
        }
      });
      setAffectedNodeIds(localSim);
    } finally {
      setSimulatingRisk(false);
    }
  };

  // Clear selections/simulations
  const resetGraph = () => {
    setSelectedNode(null);
    setRiskPropagationData(null);
    setAffectedNodeIds({});
    fetchGraph();
  };

  // Node styling helpers
  const getNodeColor = (type: string, id: string) => {
    if (riskPropagationData?.seed_node?.id === id || selectedNode?.id === id) {
      return '#00B8FF'; // Selected/Seed Node cyan
    }
    if (affectedNodeIds[id]) {
      return '#FF0055'; // High risk propagation path red
    }
    switch (type.toLowerCase()) {
      case 'asset':
        return '#00B8FF'; // Cyan
      case 'exposure':
        return '#FF8A00'; // Orange
      case 'finding':
        return '#FF0055'; // Pink/Red
      default:
        return '#9D4DFF'; // Purple
    }
  };

  // Render edge line
  const isPropagationEdge = (edge: Edge) => {
    return (
      (edge.source === selectedNode?.id && affectedNodeIds[edge.target] !== undefined) ||
      (affectedNodeIds[edge.source] !== undefined && affectedNodeIds[edge.target] !== undefined)
    );
  };

  const getEdgeStroke = (edge: Edge) => {
    if (isPropagationEdge(edge)) {
      return 'url(#redGlowGrad)';
    }
    return 'rgba(255,255,255,0.1)';
  };

  const getEdgeWidth = (edge: Edge) => {
    return isPropagationEdge(edge) ? 3 : 1.5;
  };

  // Compile detailed mock structure for side panel integration
  const compiledAnalysis = useMemo(() => {
    const centerAsset = selectedNode?.metadata?.hostname 
      ? { hostname: selectedNode.metadata.hostname, id: selectedNode.reference_id }
      : { hostname: selectedNode?.label || 'Asset', id: selectedNode?.reference_id || 'ref' };
    
    return {
      severity: selectedNode?.metadata?.severity || 'info',
      paths: edges
        .filter(e => e.source === selectedNode?.id || e.target === selectedNode?.id)
        .map(e => ({
          source_asset: { hostname: nodes.find(n => n.id === e.source)?.label || 'Src' },
          target_asset: { hostname: nodes.find(n => n.id === e.target)?.label || 'Dest' },
          severity: 'high',
          summary: `Observed trust relationship propagation: ${e.type}`,
          exploitability_score: 8.2,
          amplification: 1.5,
        })),
      blast_radius: {
        severity: selectedNode?.metadata?.severity || 'high',
        impact_score: selectedNode?.metadata?.risk_score 
          ? Math.round(selectedNode.metadata.risk_score * 10) 
          : 65,
        summary: `Compromise of this node violates logical boundaries. Outward connections expose up to ${Object.keys(affectedNodeIds).length || 2} nodes.`,
        affected_assets: Object.keys(affectedNodeIds).map(id => nodes.find(n => n.id === id)?.label).filter(Boolean) as string[],
      },
      business_impact: { business_impact_score: 75 },
      trust_boundary: { boundary_risk: 80 },
      privilege_chain: { severity: 'high' },
      ai_verdict: true
    };
  }, [selectedNode, edges, nodes, affectedNodeIds]);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-3xl font-bold text-white">🕸 Cyber Exposure Graph & Attack Paths</h1>
            <Badge variant="info">Realtime Topography</Badge>
          </div>
          <p className="text-gray-400 text-sm">
            Interactive, org-isolated security map displaying vulnerability propagation, blast radius vectors, and traversal logic.
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" className="px-4 py-2" onClick={resetGraph} disabled={loading}>
            Reset View
          </Button>
          <Button variant="primary" className="px-4 py-2" onClick={fetchGraph} disabled={loading}>
            Refresh Graph
          </Button>
        </div>
      </div>

      {/* Main Grid: Interactive Canvas & Sidebar Panel */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        
        {/* Graph Canvas */}
        <Card className="p-0 overflow-hidden relative border border-white/10 bg-[#070913]/90 shadow-2xl rounded-2xl min-h-[500px]">
          {loading && (
            <div className="absolute inset-0 bg-[#070913]/70 backdrop-blur-sm z-30 flex items-center justify-center">
              <div className="text-center">
                <Spinner className="w-10 h-10 text-cyan-400 mx-auto mb-4" />
                <p className="text-gray-400 text-sm">Calculating cyber topology layout...</p>
              </div>
            </div>
          )}

          {error && !loading && (
            <div className="absolute top-4 left-4 right-4 z-20 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400">
              ℹ Offline Mode: {error}
            </div>
          )}

          {/* SVG Node Link Panel */}
          <svg
            ref={svgRef}
            width="100%"
            height={500}
            className="select-none cursor-grab active:cursor-grabbing"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <defs>
              {/* Arrow Head definition */}
              <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.2)" />
              </marker>
              <marker id="arrowRed" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF0055" />
              </marker>

              {/* Gradient glow definitions */}
              <linearGradient id="redGlowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FF0055" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#FF8A00" stopOpacity="0.8" />
              </linearGradient>
            </defs>

            {/* Render Edges */}
            {edges.map((edge) => {
              const sourceNode = nodes.find(n => n.id === edge.source);
              const targetNode = nodes.find(n => n.id === edge.target);
              if (!sourceNode || !targetNode) return null;

              const x1 = sourceNode.x || 0;
              const y1 = sourceNode.y || 0;
              const x2 = targetNode.x || 0;
              const y2 = targetNode.y || 0;

              const isProp = isPropagationEdge(edge);

              return (
                <g key={edge.id}>
                  {isProp && (
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#FF0055"
                      strokeWidth={6}
                      strokeLinecap="round"
                      opacity={0.3}
                      className="blur-sm"
                    />
                  )}
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={getEdgeStroke(edge)}
                    strokeWidth={getEdgeWidth(edge)}
                    markerEnd={isProp ? 'url(#arrowRed)' : 'url(#arrow)'}
                    strokeDasharray={isProp ? '6,6' : undefined}
                    className={isProp ? 'animate-[dash_2s_linear_infinite]' : undefined}
                  />
                  {isProp && (
                    <style>{`
                      @keyframes dash {
                        to {
                          stroke-dashoffset: -20;
                        }
                      }
                    `}</style>
                  )}
                </g>
              );
            })}

            {/* Render Nodes */}
            {nodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              const hasRisk = affectedNodeIds[node.id] !== undefined;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x || 0}, ${node.y || 0})`}
                  onMouseDown={(e) => handleMouseDown(e, node.id)}
                  className="cursor-pointer group"
                >
                  {/* Selected / Propagated Risk Halo Glow */}
                  {(isSelected || hasRisk) && (
                    <circle
                      r={24}
                      fill="none"
                      stroke={getNodeColor(node.type, node.id)}
                      strokeWidth={2}
                      className="animate-ping opacity-25"
                    />
                  )}
                  
                  {/* Base Circle */}
                  <circle
                    r={18}
                    fill="#0F1423"
                    stroke={getNodeColor(node.type, node.id)}
                    strokeWidth={isSelected ? 3 : 1.8}
                    className="transition-colors shadow-lg group-hover:fill-[#1E293B]"
                  />

                  {/* Icon Indicator inside Node */}
                  <text
                    y={4}
                    textAnchor="middle"
                    fill={getNodeColor(node.type, node.id)}
                    fontSize={11}
                    fontWeight="bold"
                    className="pointer-events-none select-none font-mono"
                  >
                    {node.type.substring(0, 2).toUpperCase()}
                  </text>

                  {/* Label tooltip */}
                  <text
                    y={32}
                    textAnchor="middle"
                    fill={isSelected ? '#00B8FF' : '#E2E8F0'}
                    fontSize={11}
                    fontWeight={isSelected ? 'bold' : 'normal'}
                    className="pointer-events-none select-none drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Graph Legend overlay */}
          <div className="absolute bottom-4 left-4 flex space-x-4 bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs backdrop-blur-md">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span> Asset</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-orange-400"></span> Exposure</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#FF0055]"></span> Finding</span>
            {selectedNode && <span className="text-[#00B8FF]">• Selected</span>}
          </div>
        </Card>

        {/* Sidebar Controls */}
        <div className="space-y-6">
          <Card>
            <h3 className="text-md font-semibold text-white mb-4 border-b border-white/5 pb-2">Analysis Deck</h3>
            
            {selectedNode ? (
              <div className="space-y-5">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs uppercase tracking-[0.24em] text-slate-400 font-mono">
                      {selectedNode.type} Node
                    </span>
                    {selectedNode.metadata?.risk_score && (
                      <Badge variant="critical">
                        Risk: {selectedNode.metadata.risk_score}
                      </Badge>
                    )}
                  </div>
                  <h4 className="text-lg font-bold text-white leading-tight">{selectedNode.label}</h4>
                  <p className="text-xs font-mono text-gray-500 mt-1 break-all">ID: {selectedNode.reference_id}</p>
                </div>

                {/* Traversal parameters */}
                <div className="space-y-3 border-t border-white/5 pt-3">
                  <div className="text-xs font-semibold text-slate-300">Bounded Traversal Controls</div>
                  
                  <div>
                    <label className="text-[10px] text-gray-400 block mb-1">Max Hops (Depth)</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="5" 
                      value={traversalDepth} 
                      onChange={e => setTraversalDepth(Number(e.target.value))}
                      className="w-full accent-cyan-400"
                    />
                    <div className="flex justify-between text-[10px] text-gray-500 font-mono mt-1">
                      <span>1 hop</span>
                      <span>{traversalDepth} hops</span>
                      <span>5 hops</span>
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] text-gray-400 block mb-1">Direction</label>
                    <select
                      value={traversalDirection}
                      onChange={e => setTraversalDirection(e.target.value as any)}
                      className="w-full bg-slate-900 border border-white/10 rounded px-2 py-1 text-xs text-white"
                    >
                      <option value="outgoing">Outgoing Connections</option>
                      <option value="incoming">Incoming Connections</option>
                      <option value="both">Bidirectional</option>
                    </select>
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      className="flex-1 text-xs py-1.5"
                      onClick={handleTraverse}
                      disabled={traversing}
                    >
                      {traversing ? 'Loading...' : '🔍 Traverse'}
                    </Button>

                    <Button 
                      variant="primary" 
                      className="flex-1 text-xs py-1.5"
                      onClick={handleSimulateRisk}
                      disabled={simulatingRisk}
                    >
                      {simulatingRisk ? 'Simulating...' : '⚡ Simulate Risk'}
                    </Button>
                  </div>
                </div>

                {/* Simulation Output Overview */}
                {Object.keys(affectedNodeIds).length > 0 && (
                  <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs space-y-2">
                    <div className="font-semibold text-red-400 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
                      Blast Threat Active
                    </div>
                    <p className="text-gray-300">
                      Simulated compromise impacts <span className="font-bold text-white">{Object.keys(affectedNodeIds).length}</span> neighboring entities.
                    </p>
                    <div className="max-h-24 overflow-y-auto custom-scrollbar text-[10px] font-mono text-gray-400 space-y-1">
                      {Object.keys(affectedNodeIds).map(id => {
                        const nodeName = nodes.find(n => n.id === id)?.label || id;
                        return (
                          <div key={id} className="flex justify-between border-b border-white/5 py-0.5">
                            <span className="truncate max-w-[180px]">{nodeName}</span>
                            <span className="text-red-400">+{affectedNodeIds[id]} score</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-10 text-gray-500 text-sm">
                <svg className="w-8 h-8 mx-auto mb-2 opacity-40 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                </svg>
                Select any node on the graph map to review blast routes, trace access, and run traversal simulations.
              </div>
            )}
          </Card>
        </div>

      </div>

      {/* Tabs for modular analysis components */}
      {selectedNode && (
        <Card className="rounded-2xl border border-white/10 bg-[#070913]/90">
          <div className="flex border-b border-white/5 mb-4">
            <button
              onClick={() => setGraphTab('reasoning')}
              className={`pb-2.5 px-4 text-sm font-semibold border-b-2 transition ${graphTab === 'reasoning' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
            >
              Attack Reasoning Chain
            </button>
            <button
              onClick={() => setGraphTab('blast')}
              className={`pb-2.5 px-4 text-sm font-semibold border-b-2 transition ${graphTab === 'blast' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
            >
              Blast Radius Mapping
            </button>
            <button
              onClick={() => setGraphTab('lateral')}
              className={`pb-2.5 px-4 text-sm font-semibold border-b-2 transition ${graphTab === 'lateral' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
            >
              Lateral Pivot simulation
            </button>
            <button
              onClick={() => setGraphTab('privilege')}
              className={`pb-2.5 px-4 text-sm font-semibold border-b-2 transition ${graphTab === 'privilege' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
            >
              Privilege escalations
            </button>
          </div>

          <div className="p-1">
            {graphTab === 'reasoning' && (
              <AttackPathVisualizer analysis={compiledAnalysis} loading={simulatingRisk} />
            )}
            {graphTab === 'blast' && (
              <BlastRadiusPanel blastRadius={compiledAnalysis.blast_radius} loading={simulatingRisk} />
            )}
            {graphTab === 'lateral' && (
              <LateralMovementView
                movement={{
                  movement_score: selectedNode.metadata?.risk_score ? Math.round(selectedNode.metadata.risk_score * 8) : 55,
                  severity: selectedNode.metadata?.severity || 'medium',
                  summary: 'Simulated lateral hopping paths mapping Active Directory trust boundaries.',
                  pivot_paths: Object.keys(affectedNodeIds).map(id => ({
                    asset_id: id,
                    hostname: nodes.find(n => n.id === id)?.label || id,
                    pivot_score: Math.round((affectedNodeIds[id] || 0.5) * 10),
                    reason: `Exposed to ${selectedNode.label} via transitive authorization token trust.`
                  }))
                }}
                loading={simulatingRisk}
              />
            )}
            {graphTab === 'privilege' && (
              <PrivilegeChainExplorer
                privilegeChain={{
                  severity: selectedNode.metadata?.severity || 'medium',
                  transitions: [
                    { role: 'anonymous', target_role: 'read-only user', escalation: 7.2, permission: 'GET /api/v1/assets' },
                    { role: 'read-only user', target_role: 'system administrator', escalation: 9.4, permission: 'POST /api/v1/system' }
                  ]
                }}
                authInheritance={{
                  auth_inheritance_risk: 75,
                  trust_tokens: Object.keys(affectedNodeIds).map(id => ({
                    source: selectedNode.label,
                    target: nodes.find(n => n.id === id)?.label || id,
                    token_type: 'JSON Web Token (OIDC)',
                    delegation: true
                  }))
                }}
                loading={simulatingRisk}
              />
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
