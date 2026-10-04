import { HealthStatus } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  activeProvider: string;
  activeModel: string;
  onProviderClick: () => void;
}

export function Header({ health, activeProvider, activeModel, onProviderClick }: HeaderProps) {
  const status = health?.status ?? 'unknown';

  const degradedReason = (() => {
    if (!health || status === 'ready') return null;
    const c = health.checks;
    if (c.database?.status === 'down') return 'Database unreachable';
    if (c.ollama?.status === 'down') return 'Ollama unreachable - start Ollama on your host';
    if (!c.ollama?.model_present) return `Model missing - run: ollama pull ${c.ollama?.model}`;
    if (c.index_populated?.status === 'empty') return 'Index empty - run: make ingest';
    return 'System degraded';
  })();

  const shortModel = activeModel.split(':')[0];

  return (
    <header className="app-header">
      <div className="header-logo" aria-label="Lenny Growth Assistant">
        <div className="header-logo-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 4C6 3.44772 6.44772 3 7 3H10C10.5523 3 11 3.44772 11 4V16H18C18.5523 16 19 16.4477 19 17V19C19 19.5523 18.5523 20 18 20H7C6.44772 20 6 19.5523 6 19V4Z" fill="currentColor"/>
          </svg>
        </div>
        <span>Lenny</span>
      </div>

      {degradedReason && (
        <div className="header-degraded-pill" role="alert" aria-live="polite">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
            <line x1="12" x2="12" y1="9" y2="13"/>
            <line x1="12" x2="12.01" y1="17" y2="17"/>
          </svg>
          <span>{degradedReason}</span>
        </div>
      )}

      <div className="header-spacer" />

      <button
        className="provider-badge"
        onClick={onProviderClick}
        aria-label={`Provider: ${activeProvider} · ${activeModel}. Click to switch.`}
      >
        <span
          className={`health-dot ${status}`}
          role="img"
          aria-label={`Status: ${status}`}
        />
        <span className="provider-name">{activeProvider}</span>
        <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
        <span style={{ maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {shortModel}
        </span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ opacity: 0.5 }}>
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </header>
  );
}
