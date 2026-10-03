import { useState } from 'react';
import { Provider } from '../types';

interface ProviderModalProps {
  providers: Provider[];
  activeProvider: string;
  activeModel: string;
  onSelect: (provider: string, model: string) => void;
  onClose: () => void;
}

export function ProviderModal({ providers, activeProvider, activeModel, onSelect, onClose }: ProviderModalProps) {
  const [selectedProvider, setSelectedProvider] = useState(activeProvider);
  
  const currentProviderConfig = providers.find(p => p.name === selectedProvider);
  const selectedModel = currentProviderConfig?.models.chat || activeModel;

  const handleConfirm = () => {
    onSelect(selectedProvider, selectedModel);
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2 id="modal-title" className="modal-title">Model Settings</h2>
        <p className="modal-sub">Choose which AI provider powers your responses.</p>
        
        <div className="provider-list" role="radiogroup">
          {providers.map(p => {
            const isSelected = p.name === selectedProvider;
            const isDisabled = !p.available;
            
            return (
              <div 
                key={p.name}
                className={`provider-option ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                onClick={() => !isDisabled && setSelectedProvider(p.name)}
                role="radio"
                aria-checked={isSelected}
                aria-disabled={isDisabled}
                tabIndex={isDisabled ? -1 : 0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    if (!isDisabled) setSelectedProvider(p.name);
                  }
                }}
              >
                <div className="provider-radio">
                  <div className="provider-radio-dot" />
                </div>
                
                <div className="provider-info">
                  <div className="provider-info-name">
                    {p.name === 'ollama' ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                        <line x1="8" y1="21" x2="16" y2="21"/>
                        <line x1="12" y1="17" x2="12" y2="21"/>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
                      </svg>
                    )}
                    {p.name}
                  </div>
                  <div className="provider-info-model">
                    {p.models.chat}
                  </div>
                  {isDisabled && p.reason && (
                    <div className="provider-info-reason">
                      {p.reason}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button 
            className="btn-primary" 
            onClick={handleConfirm}
            disabled={selectedProvider === activeProvider && selectedModel === activeModel}
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
