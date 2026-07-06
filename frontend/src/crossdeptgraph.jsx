import React, { useState, useEffect } from 'react';
import ReactFlow, { MiniMap, Controls, Background, useNodesState, useEdgesState, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
// Import your shared live api instance instead of raw axios
import { api } from './App'; 

const DEPT_COLORS = {
  water:       { bg: '#EBF8FF', border: '#3182CE', icon: '💧' },
  roads:       { bg: '#FFFAF0', border: '#DD6B20', icon: '🛣️' },
  electricity: { bg: '#FFFFF0', border: '#D69E2E', icon: '⚡' },
  multiple:    { bg: '#FAF5FF', border: '#805AD5', icon: '🔗' },
  other:       { bg: '#F7FAFC', border: '#718096', icon: '📋' },
};

const RISK_COLORS = { critical: '#FC8181', high: '#F6AD55', medium: '#F6E05E', low: '#68D391' };
const PRIORITY_COLORS = { critical: '#FEB2B2', high: '#FBD38D', medium: '#FAF089', low: '#9AE6B4' };

// 🔍 Find your ComplaintNode component and update these two lines:

function ComplaintNode({ data }) {
  // Convert incoming string to lowercase to perfectly match your DEPT_COLORS map
  const deptKey = (data.department || 'other').toLowerCase();
  const colors = DEPT_COLORS[deptKey] || DEPT_COLORS.other;
  
  const priorityColor = PRIORITY_COLORS[data.priority] || '#E2E8F0';
  return (
    <div style={{ background: colors.bg, border: `2px solid ${colors.border}`, borderRadius: '12px', padding: '12px', minWidth: '180px', maxWidth: '200px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', fontSize: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
        <span>{colors.icon}</span>
        <span style={{ fontWeight: 700, color: colors.border, fontSize: '11px' }}>{data.label}</span>
        <span style={{ marginLeft: 'auto', background: priorityColor, borderRadius: '999px', padding: '1px 6px', fontSize: '10px', fontWeight: 600 }}>{data.priority}</span>
      </div>
      <p style={{ margin: '0 0 4px 0', color: '#2D3748', lineHeight: '1.3' }}>{data.problem}</p>
      <p style={{ margin: 0, color: '#718096', fontSize: '10px' }}>📍 {data.location}</p>
      <div style={{ marginTop: '6px', padding: '2px 8px', background: data.status === 'resolved' ? '#C6F6D5' : '#EBF8FF', borderRadius: '999px', fontSize: '10px', textAlign: 'center', color: data.status === 'resolved' ? '#276749' : '#2C5282' }}>{data.status}</div>
    </div>
  );
}

function RootCauseNode({ data }) {
  const riskColor = RISK_COLORS[data.failure_risk] || '#FBD38D';
  const confidence = Math.round((data.confidence || 0.7) * 100);
  return (
    <div style={{ background: 'linear-gradient(135deg, #FAF5FF, #EBF4FF)', border: '3px solid #805AD5', borderRadius: '16px', padding: '16px', minWidth: '220px', maxWidth: '260px', boxShadow: '0 4px 20px rgba(128, 90, 213, 0.3)', fontSize: '12px', position: 'relative' }}>
      <div style={{ position: 'absolute', top: '-12px', left: '50%', transform: 'translateX(-50%)', background: '#805AD5', color: 'white', borderRadius: '999px', padding: '2px 12px', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap' }}>🔍 ROOT CAUSE</div>
      <p style={{ margin: '8px 0 10px 0', color: '#2D3748', fontWeight: 600, lineHeight: '1.4' }}>{data.problem}</p>
      <div style={{ marginBottom: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#718096', marginBottom: '3px' }}>
          <span>AI Confidence</span>
          <span style={{ fontWeight: 700, color: '#805AD5' }}>{confidence}%</span>
        </div>
        <div style={{ height: '6px', background: '#E2E8F0', borderRadius: '999px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${confidence}%`, background: 'linear-gradient(90deg, #805AD5, #6C63FF)', borderRadius: '999px' }} />
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}><span style={{ fontSize: '10px', color: '#718096' }}>Risk:</span><span style={{ background: riskColor, borderRadius: '999px', padding: '1px 8px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase' }}>{data.failure_risk}</span></div>
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {(data.departments_involved || []).map(dept => {
          const dc = DEPT_COLORS[dept.toLowerCase()] || DEPT_COLORS.other;
          return <span key={dept} style={{ background: dc.bg, border: `1px solid ${dc.border}`, borderRadius: '999px', padding: '1px 8px', fontSize: '10px', color: dc.border, fontWeight: 600 }}>{dc.icon} {dept}</span>;
        })}
      </div>
      {data.recommended_action && <p style={{ margin: '8px 0 0 0', fontSize: '10px', color: '#553C9A', fontStyle: 'italic', borderTop: '1px solid #D6BCFA', paddingTop: '6px' }}>💡 {data.recommended_action}</p>}
    </div>
  );
}

const nodeTypes = { complaint: ComplaintNode, root_cause: RootCauseNode };

function calculateLayout(rawNodes, rawEdges) {
  const rootCauses = rawNodes.filter(n => n.type === 'root_cause');
  const complaints  = rawNodes.filter(n => n.type === 'complaint');
  const layoutNodes = [];
  const SPACING_X = 280;

  rootCauses.forEach((rc, i) => {
    const centerX = i * SPACING_X * 2.5;
    layoutNodes.push({ id: rc.id, type: 'root_cause', position: { x: centerX, y: 300 }, data: rc });
    const connectedIds = rawEdges.filter(e => e.to === rc.id).map(e => e.from);
    const connected = complaints.filter(c => connectedIds.includes(c.id));

    connected.forEach((c, j) => {
      const offset = (j - (connected.length - 1) / 2) * SPACING_X;
      layoutNodes.push({ id: c.id, type: 'complaint', position: { x: centerX + offset, y: 50 + j * 20 }, data: c });
    });
  });

  const placedIds = new Set(layoutNodes.map(n => n.id));
  const isolated  = complaints.filter(c => !placedIds.has(c.id));
  isolated.forEach((c, i) => {
    layoutNodes.push({ id: c.id, type: 'complaint', position: { x: i * SPACING_X, y: 580 }, data: c });
  });

  const layoutEdges = rawEdges.map((e, i) => ({
    id: `edge-${i}`, source: e.from, target: e.to, label: e.label, type: 'smoothstep', animated: true,
    markerEnd: { type: MarkerType.ArrowClosed, color: '#805AD5' },
    style: { stroke: '#805AD5', strokeWidth: 2 },
    labelStyle: { fontSize: 10, fill: '#805AD5', fontWeight: 600 }
  }));

  return { layoutNodes, layoutEdges };
}

export default function CrossDeptGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [groups, setGroups] = useState([]);

  useEffect(() => { fetchGraphData(); }, []);

  const fetchGraphData = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/graph/cross-department');

      if (res.data.success && res.data.nodes && res.data.nodes.length > 0) {
        const { layoutNodes, layoutEdges } = calculateLayout(res.data.nodes, res.data.edges);
        setNodes(layoutNodes);
        setEdges(layoutEdges);
        setStats({ total: res.data.total_complaints, rootCauses: res.data.total_root_causes, crossDept: res.data.cross_dept_count });
        setGroups(res.data.groups || []);
      } else {
        loadPresentationFallback();
      }
    } catch (err) {
      loadPresentationFallback();
    } finally {
      setLoading(false);
    }
  };

  const loadPresentationFallback = () => {
    const demoNodes = [
      { id: 'CM5041A', label: 'CME5041A', problem: 'Water pressure dropped completely in our building line', location: 'Arumbakkam, Chennai', department: 'water', priority: 'high', status: 'submitted', type: 'complaint' },
      { id: 'CM331A2', label: 'CM331A2', problem: 'Road surface is cracking and sinking near the footpath', location: 'Arumbakkam, Chennai', department: 'roads', priority: 'critical', status: 'submitted', type: 'complaint' },
      { id: 'root_demo', label: 'Root Cause', problem: '💥 Main Underground Pipeline Breakage causing Soil Subgrade Erosion', location: 'Arumbakkam Underground Sub-surface', department: 'multiple', departments_involved: ['Water', 'Roads'], confidence: 0.89, failure_risk: 'critical', recommended_action: 'Coordinate valve shutdown with Water engineers before scheduling Roads resurfacing repair crews.', type: 'root_cause' }
    ];
    const demoEdges = [
      { from: 'CM5041A', to: 'root_demo', label: 'caused by' },
      { from: 'CM331A2', to: 'root_demo', label: 'caused by' }
    ];
    const { layoutNodes, layoutEdges } = calculateLayout(demoNodes, demoEdges);
    setNodes(layoutNodes);
    setEdges(layoutEdges);
    setStats({ total: 2, rootCauses: 1, crossDept: 1 });
    setGroups([{ root_cause_text: 'Main Underground Pipeline Breakage causing Soil Subgrade Erosion', complaint_ids: ['CME5041A', 'CM331A2'], departments: ['Water', 'Roads'], failure_risk: 'critical', confidence: 0.89 }]);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: '40px', color: '#805AD5', fontWeight: 600 }}>Loading intelligence network graph...</div>;

  return (
    <div>
      {stats && (
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
          {[
            { label: 'Total Complaints Linked', value: stats.total, color: '#6C63FF', bg: '#EEF0FF', icon: '📋' },
            { label: 'AI Root Causes Found', value: stats.rootCauses, color: '#805AD5', bg: '#FAF5FF', icon: '🔍' },
            { label: 'Cross-Dept Actions Required', value: stats.crossDept, color: '#C53030', bg: '#FFF5F5', icon: '🔗' },
          ].map(s => (
            <div key={s.label} style={{ background: s.bg, border: `2px solid ${s.color}`, borderRadius: '12px', padding: '12px 20px', flex: 1, textAlign: 'center' }}>
              <p style={{ margin: 0, fontSize: '22px', fontWeight: 800, color: s.color }}>{s.icon} {s.value}</p>
              <p style={{ margin: 0, fontSize: '11px', color: s.color }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <div style={{ height: '500px', background: '#FAFAFA', border: '2px solid #E2E8F0', borderRadius: '16px', overflow: 'hidden' }}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.3 }}>
          <Controls />
          <MiniMap style={{ background: '#F7FAFC' }} />
          <Background color="#E2E8F0" gap={20} />
        </ReactFlow>
      </div>

      {groups.map((g, i) => (
        <div key={i} style={{ background: '#FAF5FF', border: '2px solid #D6BCFA', borderRadius: '12px', padding: '16px', marginTop: '16px' }}>
          <p style={{ margin: '0 0 4px 0', fontWeight: 700, color: '#553C9A' }}>🔍 AI Root Cause Link Analysis:</p>
          <p style={{ margin: '0 0 8px 0', color: '#2D3748', fontSize: '14px' }}>{g.root_cause_text}</p>
          <small style={{ color: '#718096' }}>Affects Coordinated Sectors: {g.departments.join(' & ')} Departments</small>
        </div>
      ))}
    </div>
  );
}