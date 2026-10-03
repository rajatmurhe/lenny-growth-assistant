import { useEffect, useState } from 'react';
import { API_BASE } from '../api';

interface ArtifactViewerProps {
  artifactId: string;
}

interface Artifact {
  id: string;
  title: string;
  type: string;
  content: string;
  sanitized_content: string;
}

export function ArtifactViewer({ artifactId }: ArtifactViewerProps) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');

  useEffect(() => {
    fetch(`${API_BASE}/artifacts/${artifactId}`)
      .then(res => res.json())
      .then(data => setArtifact(data))
      .catch(console.error);
  }, [artifactId]);

  if (!artifact) {
    return (
      <aside className="artifact-pane">
        <div className="artifact-pane-empty">
          <div className="artifact-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="9" y1="21" x2="9" y2="9"/>
            </svg>
          </div>
          <div className="artifact-empty-title">Artifact Viewer</div>
          <div className="artifact-empty-sub">
            Generated documents, Ship 30 essays, and one-pagers will appear here.
          </div>
        </div>
      </aside>
    );
  }

  // Inject a strict CSP into the head
  const safeHtml = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:;">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #18181b; padding: 24px; margin: 0; }
          h1, h2, h3 { color: #09090b; margin-top: 1.5em; letter-spacing: -0.01em; }
          h1 { font-size: 24px; font-weight: 700; }
          h2 { font-size: 20px; font-weight: 600; }
          ul, ol { padding-left: 24px; }
          li { margin-bottom: 8px; }
          blockquote { border-left: 3px solid #e4e4e7; padding-left: 16px; margin: 16px 0; color: #52525b; font-style: italic; }
          p { margin-bottom: 16px; }
        </style>
      </head>
      <body>
        ${artifact.sanitized_content}
      </body>
    </html>
  `;

  return (
    <aside className="artifact-pane">
      <div className="artifact-header">
        <div className="artifact-type-badge">{artifact.type}</div>
        <div className="artifact-title" title={artifact.title}>{artifact.title}</div>
        <div className="artifact-actions">
          <button 
            className="btn-icon" 
            title="Copy to clipboard"
            onClick={() => navigator.clipboard.writeText(artifact.content)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
          <button 
            className="btn-icon" 
            title="Download"
            onClick={() => {
              const blob = new Blob([artifact.content], { type: 'text/markdown' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${artifact.title.replace(/\s+/g, '_').toLowerCase()}.${artifact.type === 'markdown' ? 'md' : 'html'}`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </button>
        </div>
      </div>
      
      <div className="artifact-tabs">
        <button 
          className={`artifact-tab ${viewMode === 'preview' ? 'active' : ''}`}
          onClick={() => setViewMode('preview')}
        >
          Preview
        </button>
        <button 
          className={`artifact-tab ${viewMode === 'code' ? 'active' : ''}`}
          onClick={() => setViewMode('code')}
        >
          Source Code
        </button>
      </div>

      <div className="artifact-body">
        {viewMode === 'preview' ? (
          <div className="artifact-preview">
            <iframe
              sandbox="" 
              srcDoc={safeHtml}
              title="Artifact Preview"
            />
          </div>
        ) : (
          <div className="artifact-code">
            <pre><code>{artifact.content}</code></pre>
          </div>
        )}
      </div>

      <div className="artifact-security-panel">
        <details>
          <summary>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
            Security Sandbox Active
          </summary>
          <div className="security-grid">
            <div>
              <div className="security-col-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Allowed
              </div>
              <div className="security-item">Text formatting</div>
              <div className="security-item">Headings & Lists</div>
              <div className="security-item">Inline styling</div>
            </div>
            <div>
              <div className="security-col-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
                Blocked
              </div>
              <div className="security-item">JavaScript execution</div>
              <div className="security-item">External resources</div>
              <div className="security-item">Forms & Popups</div>
            </div>
          </div>
        </details>
      </div>
    </aside>
  );
}
