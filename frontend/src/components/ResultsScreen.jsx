import React, { useEffect, useRef } from 'react';
import { Activity, RefreshCw, UserCog } from 'lucide-react';
import cytoscape from 'cytoscape';
import { marked } from 'marked';

const AgentReport = ({ report, index }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (report.diagram_json && report.diagram_json.length > 0 && containerRef.current) {
      cytoscape({
        container: containerRef.current,
        elements: report.diagram_json,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'hsl(142.1, 70.6%, 45.3%)',
              'label': 'data(label)',
              'color': '#fff',
              'text-valign': 'center',
              'text-halign': 'center',
              'font-size': '10px',
              'width': 'label',
              'height': 30,
              'padding': '10px',
              'shape': 'round-rectangle',
              'text-wrap': 'wrap',
              'text-max-width': '80px',
              'border-width': 2,
              'border-color': '#fff'
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#666',
              'target-arrow-color': '#666',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'label': 'data(label)',
              'font-size': '8px',
              'color': '#999'
            }
          }
        ],
        layout: {
          name: 'cose',
          animate: false,
          padding: 30,
          componentSpacing: 50,
          nodeOverlap: 25,
          idealEdgeLength: 60
        }
      });
    }
  }, [report.diagram_json]);

  return (
    <div className="agent-report-card" style={{ animationDelay: `${index * 0.1}s` }}>
      <div className="agent-header">
        <div className="agent-icon">
          <UserCog size={24} />
        </div>
        <div className="agent-info">
          <h3 className="agent-role">{report.role}</h3>
          <p className="agent-description">Multi-agent analysis perspective</p>
        </div>
      </div>
      <div 
        className="agent-content" 
        dangerouslySetInnerHTML={{ __html: marked(report.content) }} 
      />
      {report.diagram_json && report.diagram_json.length > 0 && (
        <div className="agent-graph-container" ref={containerRef} style={{ height: '300px', marginTop: '1rem', border: '1px solid var(--border)', borderRadius: '8px' }}></div>
      )}
    </div>
  );
};

export default function ResultsScreen({ data, onNewSimulation }) {
  if (!data || !data.reports) {
    return <div className="results-screen"><p>No simulation data available.</p></div>;
  }

  return (
    <div className="results-screen">
      <div className="results-header">
        <div className="results-title-section">
          <h2 className="results-title">
            <Activity />
            <span>Simulation Results</span>
          </h2>
          <p className="results-subtitle">AI-powered multi-agent analysis with causal modeling</p>
        </div>
        <button onClick={onNewSimulation} className="new-simulation-btn">
          <RefreshCw size={18} />
          <span>New Simulation</span>
        </button>
      </div>

      <div className="results-container">
        {data.reports.map((report, index) => (
          <AgentReport key={index} report={report} index={index} />
        ))}
      </div>
    </div>
  );
}
