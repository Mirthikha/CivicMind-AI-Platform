import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';

// ─────────────────────────────────────────
// Color maps
// ─────────────────────────────────────────
const DEPT_COLORS = {
  water:       { bg: '#EBF8FF', border: '#3182CE', icon: '💧' },
  roads:       { bg: '#FFFAF0', border: '#DD6B20', icon: '🛣️' },
  electricity: { bg: '#FFFFF0', border: '#D69E2E', icon: '⚡' },
  multiple:    { bg: '#FAF5FF', border: '#805AD5', icon: '🔗' },
  other:       { bg: '#F7FAFC', border: '#718096', icon: '📋' },
};

const RISK_COLORS = {
  critical: '#FC8181',
  high:     '#F6AD55',
  medium:   '#F6E05E',
  low:      '#68D391',
};

const PRIORITY_COLORS = {
  critical: '#FEB2B2',
  high:     '#FBD38D',
  medium:   '#FAF089',
  low:      '#9AE6B4',
};

// ─────────────────────────────────────────
// Custom Node: Complaint
// ─────────────────────────────────────────
function ComplaintNode({ data }) {
  const colors = DEPT_COLORS[data.department] || DEPT_COLORS.other;
  const priorityColor = PRIORITY_COLORS[data.priority] || '#E2E8F0';

  return (
    <div style={{
      background: colors.bg,
      border: `2px solid ${colors.border}`,
      borderRadius: '12px',
      padding: '12px',
      minWidth: '180px',
      maxWidth: '200px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      fontSize: '12px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginBottom: '6px',
      }}>
        <span>{colors.icon}</span>
        <span style={{
          fontWeight: 700,
          color: colors.border,
          fontSize: '11px',
        }}>
          {data.label}
        </span>
        <span style={{
          marginLeft: 'auto',
          background: priorityColor,
          borderRadius: '999px',
          padding: '1px 6px',
          fontSize: '10px',
          fontWeight: 600,
        }}>
          {data.priority}
        </span>
      </div>

      {/* Problem */}
      <p style={{
        margin: '0 0 4px 0',
        color: '#2D3748',
        lineHeight: '1.3',
      }}>
        {data.problem}
      </p>

      {/* Location */}
      <p style={{
        margin: 0,
        color: '#718096',
        fontSize: '10px',
      }}>
        📍 {data.location}
      </p>

      {/* Status */}
      <div style={{
        marginTop: '6px',
        padding: '2px 8px',
        background: data.status === 'resolved'
          ? '#C6F6D5' : '#EBF8FF',
        borderRadius: '999px',
        fontSize: '10px',
        textAlign: 'center',
        color: data.status === 'resolved' ? '#276749' : '#2C5282',
      }}>
        {data.status}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────
// Custom Node: Root Cause
// ─────────────────────────────────────────
function RootCauseNode({ data }) {
  const riskColor = RISK_COLORS[data.failure_risk] || '#FBD38D';
  const confidence = Math.round((data.confidence || 0.7) * 100);

  return (
    <div style={{
      background: 'linear-gradient(135deg, #FAF5FF, #EBF4FF)',
      border: '3px solid #805AD5',
      borderRadius: '16px',
      padding: '16px',
      minWidth: '220px',
      maxWidth: '260px',
      boxShadow: '0 4px 20px rgba(128, 90, 213, 0.3)',
      fontSize: '12px',
      position: 'relative',
    }}>
      {/* Badge */}
      <div style={{
        position: 'absolute',
        top: '-12px',
        left: '50%',
        transform: 'translateX(-50%)',
        background: '#805AD5',
        color: 'white',
        borderRadius: '999px',
        padding: '2px 12px',
        fontSize: '11px',
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}>
        🔍 ROOT CAUSE
      </div>

      {/* Root cause text */}
      <p style={{
        margin: '8px 0 10px 0',
        color: '#2D3748',
        fontWeight: 600,
        lineHeight: '1.4',
      }}>
        {data.problem}
      </p>

      {/* Confidence bar */}
      <div style={{ marginBottom: '8px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '10px',
          color: '#718096',
          marginBottom: '3px',
        }}>
          <span>AI Confidence</span>
          <span style={{ fontWeight: 700, color: '#805AD5' }}>
            {confidence}%
          </span>
        </div>
        <div style={{
          height: '6px',
          background: '#E2E8F0',
          borderRadius: '999px',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${confidence}%`,
            background: 'linear-gradient(90deg, #805AD5, #6C63FF)',
            borderRadius: '999px',
          }} />
        </div>
      </div>

      {/* Risk level */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginBottom: '8px',
      }}>
        <span style={{ fontSize: '10px', color: '#718096' }}>
          Risk:
        </span>
        <span style={{
          background: riskColor,
          borderRadius: '999px',
          padding: '1px 8px',
          fontSize: '10px',
          fontWeight: 700,
          textTransform: 'uppercase',
        }}>
          {data.failure_risk}
        </span>
      </div>

      {/* Departments */}
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {(data.departments_involved || []).map(dept => {
          const dc = DEPT_COLORS[dept] || DEPT_COLORS.other;
          return (
            <span key={dept} style={{
              background: dc.bg,
              border: `1px solid ${dc.border}`,
              borderRadius: '999px',
              padding: '1px 8px',
              fontSize: '10px',
              color: dc.border,
              fontWeight: 600,
            }}>
              {dc.icon} {dept}
            </span>
          );
        })}
      </div>

      {/* Action */}
      {data.recommended_action && (
        <p style={{
          margin: '8px 0 0 0',
          fontSize: '10px',
          color: '#553C9A',
          fontStyle: 'italic',
          borderTop: '1px solid #D6BCFA',
          paddingTop: '6px',
        }}>
          💡 {data.recommended_action}
        </p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────
// Register node types
// ─────────────────────────────────────────
const nodeTypes = {
  complaint:  ComplaintNode,
  root_cause: RootCauseNode,
};

// ─────────────────────────────────────────
// Layout calculator
// ─────────────────────────────────────────
function calculateLayout(rawNodes, rawEdges) {
  const rootCauses = rawNodes.filter(n => n.type === 'root_cause');
  const complaints  = rawNodes.filter(n => n.type === 'complaint');

  const layoutNodes = [];
  const SPACING_X = 280;
  const SPACING_Y = 220;

  // Place root causes in the center row
  rootCauses.forEach((rc, i) => {
    const centerX = i * SPACING_X * 2.5;
    layoutNodes.push({
      id:       rc.id,
      type:     'root_cause',
      position: { x: centerX, y: 300 },
      data:     rc,
    });

    // Find complaints connected to this root cause
    const connectedIds = rawEdges
      .filter(e => e.to === rc.id)
      .map(e => e.from);

    const connected = complaints.filter(
      c => connectedIds.includes(c.id)
    );

    // Place connected complaints above root cause
    connected.forEach((c, j) => {
      const offset = (j - (connected.length - 1) / 2) * SPACING_X;
      layoutNodes.push({
        id:       c.id,
        type:     'complaint',
        position: { x: centerX + offset, y: 50 + j * 20 },
        data:     c,
      });
    });
  });

  // Place isolated complaints (no cross-dept link) below
  const placedIds = new Set(layoutNodes.map(n => n.id));
  const isolated  = complaints.filter(c => !placedIds.has(c.id));

  isolated.forEach((c, i) => {
    layoutNodes.push({
      id:       c.id,
      type:     'complaint',
      position: { x: i * SPACING_X, y: 580 },
      data:     c,
    });
  });

  // Build ReactFlow edges
  const layoutEdges = rawEdges.map((e, i) => ({
    id:             `edge-${i}`,
    source:         e.from,
    target:         e.to,
    label:          e.label,
    type:           'smoothstep',
    animated:       true,
    markerEnd: {
      type:  MarkerType.ArrowClosed,
      color: '#805AD5',
    },
    style: {
      stroke:      '#805AD5',
      strokeWidth: 2,
    },
    labelStyle: {
      fontSize:   10,
      fill:       '#805AD5',
      fontWeight: 600,
    },
  }));

  return { layoutNodes, layoutEdges };
}

// ─────────────────────────────────────────
// Main CrossDeptGraph Component
// ─────────────────────────────────────────
export default function CrossDeptGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [stats, setStats]     = useState(null);
  const [groups, setGroups]   = useState([]);

  useEffect(() => {
    fetchGraphData();
  }, []);

  const fetchGraphData = async () => {
    try {
      setLoading(true);
      const res = await axios.get(
        'http://localhost:8000/api/graph/cross-department'
      );

      if (res.data.success) {
        const { layoutNodes, layoutEdges } = calculateLayout(
          res.data.nodes,
          res.data.edges
        );
        setNodes(layoutNodes);
        setEdges(layoutEdges);
        setStats({
          total:      res.data.total_complaints,
          rootCauses: res.data.total_root_causes,
          crossDept:  res.data.cross_dept_count,
          deptSummary: res.data.department_summary,
        });
        setGroups(res.data.groups || []);
      }
    } catch (err) {
      setError('Could not load graph data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  // ── Loading ──
  if (loading) return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '500px',
      gap: '16px',
    }}>
      <div style={{
        width: '48px', height: '48px',
        border: '4px solid #E9D8FD',
        borderTopColor: '#805AD5',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
      }} />
      <p style={{ color: '#805AD5', fontWeight: 600 }}>
        Loading cross-department intelligence graph...
      </p>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );

  // ── Error ──
  if (error) return (
    <div style={{
      background: '#FFF5F5',
      border: '2px solid #FC8181',
      borderRadius: '16px',
      padding: '24px',
      textAlign: 'center',
    }}>
      <p style={{ fontSize: '32px' }}>⚠️</p>
      <p style={{ color: '#C53030', fontWeight: 600 }}>{error}</p>
      <button onClick={fetchGraphData} style={{
        background: '#805AD5',
        color: 'white',
        border: 'none',
        borderRadius: '999px',
        padding: '8px 24px',
        cursor: 'pointer',
        marginTop: '8px',
      }}>
        Try Again
      </button>
    </div>
  );

  // ── Empty ──
  if (nodes.length === 0) return (
    <div style={{
      background: 'linear-gradient(135deg, #FAF5FF, #EBF8FF)',
      border: '2px dashed #D6BCFA',
      borderRadius: '16px',
      padding: '48px',
      textAlign: 'center',
    }}>
      <p style={{ fontSize: '48px' }}>🎉</p>
      <h3 style={{ color: '#553C9A' }}>
        No Cross-Department Issues
      </h3>
      <p style={{ color: '#805AD5' }}>
        All complaints are currently isolated incidents.<br />
        Submit more complaints to see the intelligence graph.
      </p>
      <button onClick={fetchGraphData} style={{
        background: '#805AD5',
        color: 'white',
        border: 'none',
        borderRadius: '999px',
        padding: '10px 28px',
        cursor: 'pointer',
        marginTop: '16px',
        fontWeight: 600,
      }}>
        🔄 Refresh
      </button>
    </div>
  );

  // ── Main Graph ──
  return (
    <div>
      {/* Stats Bar */}
      {stats && (
        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '20px',
          flexWrap: 'wrap',
        }}>
          {[
            {
              label: 'Total Complaints',
              value: stats.total,
              color: '#6C63FF',
              bg: '#EEF0FF',
              icon: '📋',
            },
            {
              label: 'Root Causes Found',
              value: stats.rootCauses,
              color: '#805AD5',
              bg: '#FAF5FF',
              icon: '🔍',
            },
            {
              label: 'Cross-Dept Alerts',
              value: stats.crossDept,
              color: '#C53030',
              bg: '#FFF5F5',
              icon: '🔗',
            },
          ].map(s => (
            <div key={s.label} style={{
              background: s.bg,
              border: `2px solid ${s.color}`,
              borderRadius: '12px',
              padding: '12px 20px',
              minWidth: '140px',
              textAlign: 'center',
            }}>
              <p style={{
                margin: 0,
                fontSize: '24px',
                fontWeight: 800,
                color: s.color,
              }}>
                {s.icon} {s.value}
              </p>
              <p style={{
                margin: 0,
                fontSize: '11px',
                color: s.color,
              }}>
                {s.label}
              </p>
            </div>
          ))}

          <button onClick={fetchGraphData} style={{
            marginLeft: 'auto',
            background: 'white',
            border: '2px solid #805AD5',
            color: '#805AD5',
            borderRadius: '999px',
            padding: '8px 20px',
            cursor: 'pointer',
            fontWeight: 600,
            alignSelf: 'center',
          }}>
            🔄 Refresh
          </button>
        </div>
      )}

      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: '16px',
        marginBottom: '16px',
        flexWrap: 'wrap',
        fontSize: '12px',
      }}>
        <span style={{ color: '#718096' }}>Legend:</span>
        {Object.entries(DEPT_COLORS).map(([dept, c]) => (
          <span key={dept} style={{
            background: c.bg,
            border: `1px solid ${c.border}`,
            borderRadius: '999px',
            padding: '2px 10px',
            color: c.border,
            fontWeight: 600,
          }}>
            {c.icon} {dept}
          </span>
        ))}
        <span style={{
          background: '#FAF5FF',
          border: '2px solid #805AD5',
          borderRadius: '999px',
          padding: '2px 10px',
          color: '#805AD5',
          fontWeight: 700,
        }}>
          🔍 root cause (center)
        </span>
      </div>

      {/* ReactFlow Graph */}
      <div style={{
        height: '600px',
        background: '#FAFAFA',
        border: '2px solid #E2E8F0',
        borderRadius: '16px',
        overflow: 'hidden',
      }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          attributionPosition="bottom-right"
        >
          <Controls />
          <MiniMap
            nodeColor={n =>
              n.type === 'root_cause' ? '#805AD5' : '#6C63FF'
            }
            style={{ background: '#F7FAFC' }}
          />
          <Background color="#E2E8F0" gap={20} />
        </ReactFlow>
      </div>

      {/* Groups Summary */}
      {groups.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <h3 style={{
            color: '#2D3748',
            fontFamily: 'Poppins, sans-serif',
            marginBottom: '12px',
          }}>
            🔗 Linked Issue Groups
          </h3>
          {groups.map((g, i) => (
            <div key={i} style={{
              background: '#FAF5FF',
              border: '2px solid #D6BCFA',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '12px',
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                flexWrap: 'wrap',
                gap: '8px',
              }}>
                <div>
                  <p style={{
                    margin: '0 0 4px 0',
                    fontWeight: 700,
                    color: '#553C9A',
                  }}>
                    🔍 {g.root_cause_text}
                  </p>
                  <p style={{
                    margin: 0,
                    fontSize: '12px',
                    color: '#718096',
                  }}>
                    {g.complaint_ids.length} complaints linked •{' '}
                    {g.departments.join(', ')} departments
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span style={{
                    background: RISK_COLORS[g.failure_risk] || '#FBD38D',
                    borderRadius: '999px',
                    padding: '2px 12px',
                    fontSize: '12px',
                    fontWeight: 700,
                  }}>
                    {g.failure_risk} risk
                  </span>
                  <span style={{
                    background: '#EBF8FF',
                    color: '#2C5282',
                    borderRadius: '999px',
                    padding: '2px 12px',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}>
                    {Math.round(g.confidence * 100)}% confidence
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}