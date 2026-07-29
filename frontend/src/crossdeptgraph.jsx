import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link as LinkIcon, AlertTriangle, CheckCircle, ArrowRight, RefreshCw, Zap } from 'lucide-react';

const API_BASE = "https://civicmind-ai-platform.onrender.com";

// Default fallback linked complaints showing shared root cause
const sampleLinkedClusters = [
  {
    cluster_id: "CLUSTER-101",
    shared_root_cause: "Main Underground Pipeline Rupture & Subsurface Erosion",
    primary_department: "Water Department",
    secondary_departments: ["Roads Department"],
    recommendation: "Water Department must fix pipe joint; Roads Dept can then repair road subsidence.",
    confidence: 94,
    complaints: [
      {
        id: "CM4G5H6I",
        problem: "Severe drinking water pipeline leakage near main junction",
        location: "Bandra West, Mumbai",
        department: "Water",
        priority: "critical"
      },
      {
        id: "CM1A2B3C",
        problem: "Large asphalt asphalt cave-in & pothole right above pipeline burst",
        location: "Bandra West, Mumbai",
        department: "Roads",
        priority: "high"
      }
    ]
  },
  {
    cluster_id: "CLUSTER-102",
    shared_root_cause: "Overhead Feeder Transformer Overload & Short Circuit",
    primary_department: "Electricity Department",
    secondary_departments: ["Traffic / Signals"],
    recommendation: "Electricity Dept replace transformer fuse to restore neighborhood streetlights and traffic signals.",
    confidence: 88,
    complaints: [
      {
        id: "CM9D8E7F",
        problem: "Streetlights completely dark for 3 consecutive nights",
        location: "Indiranagar, Bengaluru",
        department: "Electricity",
        priority: "medium"
      },
      {
        id: "CM3X2Y1Z",
        problem: "Traffic intersection signal lights blinking red / unpowered",
        location: "Indiranagar, Bengaluru",
        department: "Traffic",
        priority: "high"
      }
    ]
  }
];

export default function CrossDeptGraph() {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchClusters = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/api/officials/cross-dept-alerts`);
      const data = response.data?.alerts || response.data?.clusters || response.data;
      if (Array.isArray(data) && data.length > 0) {
        setClusters(data);
      } else {
        setClusters(sampleLinkedClusters);
      }
    } catch (err) {
      console.warn("⚠️ Cross-Dept API call failed or endpoint missing, loading fallback clusters:", err);
      setClusters(sampleLinkedClusters);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClusters();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
        <RefreshCw size={24} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
        <p style={{ marginTop: '12px', fontSize: '15px' }}>Analyzing cross-department root cause connections...</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', color: '#0f172a', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={20} color="#6366f1" /> AI Shared Root Cause Clusters
          </h2>
          <p style={{ fontSize: '14px', color: '#64748b', margin: '4px 0 0 0' }}>
            Resolving the single root action item will automatically fix all linked issues.
          </p>
        </div>
        <button 
          onClick={fetchClusters} 
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', borderRadius: '8px', border: '1px solid #cbd5e1', background: '#ffffff', cursor: 'pointer', fontSize: '13px' }}
        >
          <RefreshCw size={14} /> Refresh Graph
        </button>
      </div>

      {clusters.map((cluster, idx) => (
        <div 
          key={cluster.cluster_id || idx} 
          style={{ 
            border: '1px solid #e2e8f0', 
            borderRadius: '12px', 
            background: '#f8fafc', 
            padding: '20px', 
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)' 
          }}
        >
          {/* Header Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#6366f1', background: '#e0e7ff', padding: '4px 10px', borderRadius: '20px' }}>
                {cluster.cluster_id || `LINKED ISSUE #${idx + 1}`}
              </span>
              <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b', margin: '8px 0 0 0' }}>
                ⚡ Shared Root Cause: {cluster.shared_root_cause || cluster.root_cause}
              </h3>
            </div>
            <div style={{ background: '#f1f5f9', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', color: '#334155' }}>
              <strong>AI Confidence:</strong> <span style={{ color: '#16a34a' }}>{cluster.confidence || 90}%</span>
            </div>
          </div>

          {/* Action Recommendation Banner */}
          <div style={{ background: '#eff6ff', borderLeft: '4px solid #3b82f6', padding: '12px 16px', borderRadius: '6px', marginBottom: '20px', fontSize: '14px', color: '#1e40af' }}>
            <strong>💡 Single Solution Action: </strong> 
            {cluster.recommendation || cluster.recommended_action || "Fix primary asset to resolve downstream complaints."}
          </div>

          {/* Linked Complaints Visual Nodes */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {(cluster.complaints || cluster.linked_complaints || []).map((item, i) => (
              <div 
                key={item.id || i} 
                style={{ 
                  background: '#ffffff', 
                  border: '1px solid #cbd5e1', 
                  borderRadius: '10px', 
                  padding: '16px', 
                  position: 'relative' 
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 'bold', fontSize: '13px', background: '#f1f5f9', padding: '2px 8px', borderRadius: '4px' }}>
                    {item.id}
                  </span>
                  <span style={{ fontSize: '12px', fontWeight: '600', color: '#475569', background: '#e2e8f0', padding: '2px 8px', borderRadius: '12px' }}>
                    {item.department} Dept
                  </span>
                </div>
                <p style={{ fontSize: '14px', color: '#334155', margin: '0 0 8px 0', fontWeight: '500' }}>
                  {item.problem || item.complaint_text}
                </p>
                <small style={{ color: '#64748b' }}>📍 {item.location || "City Limits"}</small>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}