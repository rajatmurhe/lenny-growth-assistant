import { useState, useEffect, useCallback } from 'react';
import { Session, HealthStatus, Provider } from './types';
import { api } from './api';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ChatPane } from './components/ChatPane';
import { ArtifactViewer } from './components/ArtifactViewer';
import { ProviderModal } from './components/ProviderModal';
import './index.css';

type MobileTab = 'chat' | 'artifacts';

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [activeProvider, setActiveProvider] = useState('ollama');
  const [activeModel, setActiveModel] = useState('llama3.2:3b');
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<MobileTab>('chat');
  const [sessionsLoading, setSessionsLoading] = useState(true);

  // Load sessions on mount
  useEffect(() => {
    api.listSessions()
      .then(setSessions)
      .catch(console.error)
      .finally(() => setSessionsLoading(false));
  }, []);

  // Poll health every 30s
  useEffect(() => {
    const fetchHealth = () => {
      api.getHealth().then(setHealth).catch(() =>
        setHealth({ status: 'not_ready', checks: {} })
      );
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30_000);
    return () => clearInterval(interval);
  }, []);

  // Load providers
  useEffect(() => {
    api.getProviders()
      .then((data) => {
        setProviders(data.providers);
        setActiveProvider(data.active);
        const p = data.providers.find((p) => p.name === data.active);
        if (p) setActiveModel(p.models.chat);
      })
      .catch(console.error);
  }, []);

  const handleNewChat = useCallback(async () => {
    try {
      const session = await api.createSession(activeProvider);
      setSessions((prev) => [session, ...prev]);
      setActiveSession({ ...session, messages: [] });
      setActiveArtifactId(null);
    } catch (e) {
      console.error('Failed to create session', e);
    }
  }, [activeProvider]);

  const handleSelectSession = useCallback(async (id: string) => {
    try {
      const session = await api.getSession(id);
      setActiveSession(session);
      setActiveArtifactId(null);
    } catch (e) {
      console.error('Failed to load session', e);
    }
  }, []);

  // Refresh session after message sent (to get persisted messages)
  const handleMessageSent = useCallback(async (sessionId: string) => {
    try {
      const session = await api.getSession(sessionId);
      setActiveSession(session);
      // Update sessions list title
      setSessions((prev) => prev.map((s) => s.id === sessionId ? { ...s, title: session.title } : s));
    } catch (e) {
      console.error('Failed to refresh session', e);
    }
  }, []);

  const handleProviderChanged = (provider: string, model: string) => {
    setActiveProvider(provider);
    setActiveModel(model);
    if (activeSession) {
      setActiveSession((prev) => prev ? { ...prev, provider: provider as 'ollama' | 'anthropic', model } : prev);
    }
  };

  const handleArtifactCreated = (artifactId: string) => {
    setActiveArtifactId(artifactId);
    setMobileTab('artifacts');
  };

  const degraded = health && health.status !== 'ready';

  return (
    <div className="app">
      <Header
        health={health}
        activeProvider={activeSession?.provider ?? activeProvider}
        activeModel={activeSession?.model ?? activeModel}
        onProviderClick={() => setShowProviderModal(true)}
      />

      {/* Mobile tabs */}
      <div className="mobile-tabs" role="tablist" aria-label="View">
        <button
          className={`mobile-tab${mobileTab === 'chat' ? ' active' : ''}`}
          onClick={() => setMobileTab('chat')}
          role="tab"
          aria-selected={mobileTab === 'chat'}
        >
          Chat
        </button>
        <button
          className={`mobile-tab${mobileTab === 'artifacts' ? ' active' : ''}`}
          onClick={() => setMobileTab('artifacts')}
          role="tab"
          aria-selected={mobileTab === 'artifacts'}
        >
          Artifacts {activeArtifactId ? '●' : ''}
        </button>
      </div>

      <div className="app-body">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSession?.id ?? null}
          onSelect={handleSelectSession}
          onNewChat={handleNewChat}
        />

        <ChatPane
          session={activeSession}
          onNewMessage={handleMessageSent}
          onArtifactCreated={handleArtifactCreated}
          onNewChat={handleNewChat}
        />

        {activeArtifactId && (
          <ArtifactViewer artifactId={activeArtifactId} />
        )}
      </div>

      {showProviderModal && (
        <ProviderModal
          providers={providers}
          activeProvider={activeSession?.provider ?? activeProvider}
          activeModel={activeSession?.model ?? activeModel}
          onClose={() => setShowProviderModal(false)}
          onSelect={handleProviderChanged}
        />
      )}
    </div>
  );
}
