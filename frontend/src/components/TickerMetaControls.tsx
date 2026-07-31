import { useState, type FormEvent } from 'react';
import type { TickerData, WatchlistMetadata } from '../types/watchlist';
import { Icon } from './Icon';

interface TickerMetaControlsProps {
  symbol: string;
  data: TickerData;
  compact?: boolean;
  onAddTag: (ticker: string, name: string) => void;
  onRemoveTag: (ticker: string, tagNameOrId: string) => void;
  onUpdateMetadata: (ticker: string, metadata: Partial<WatchlistMetadata>) => void;
}

export function TickerMetaControls({ symbol, data, compact = false, onAddTag, onRemoveTag, onUpdateMetadata }: TickerMetaControlsProps) {
  const [addingTag, setAddingTag] = useState(false);
  const [newTag, setNewTag] = useState('');

  const submitTag = (event?: FormEvent) => {
    event?.preventDefault();
    const tag = newTag.trim().toLocaleLowerCase();
    if (tag && !data.tags.some((existing) => existing.name === tag)) onAddTag(symbol, tag);
    setNewTag('');
    setAddingTag(false);
  };

  return (
    <div className={`ticker-meta-controls${compact ? ' compact' : ''}`}>
      <div className="ticker-workflow-fields">
        <label><span>Status</span><select value={data.status || 'watching'} onChange={(event) => onUpdateMetadata(symbol, { status: event.target.value })}><option value="watching">Watching</option><option value="researching">Researching</option><option value="ready">Ready to act</option><option value="holding">Holding</option><option value="passed">Passed</option></select></label>
        <label><span>Priority</span><select value={data.priority || 'medium'} onChange={(event) => onUpdateMetadata(symbol, { priority: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
      </div>

      <div className="tag-editor">
        <div className="tag-list" aria-label={`${symbol} tags`}>
          {data.tags.map((tag) => (
            <span className="tag-chip" key={tag.id}>
              <span className="tag-dot" style={{ backgroundColor: tag.color || 'var(--accent)' }} aria-hidden="true" />
              {tag.name}
              <button type="button" onClick={() => onRemoveTag(symbol, tag.id)} aria-label={`Remove ${tag.name} tag from ${symbol}`} title={`Remove ${tag.name} tag`}><Icon name="close" size={13} /></button>
            </span>
          ))}
        </div>

        {addingTag ? (
          <form className="tag-form" onSubmit={submitTag}>
            <label className="visually-hidden" htmlFor={`tag-${symbol}`}>New tag for {symbol}</label>
            <input id={`tag-${symbol}`} type="text" value={newTag} onChange={(event) => setNewTag(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') { setAddingTag(false); setNewTag(''); } }} autoFocus placeholder="Tag name" />
            <button className="icon-button icon-button-small" type="submit" aria-label="Add tag" title="Add tag"><Icon name="check" size={15} /></button>
            <button className="icon-button icon-button-small" type="button" onClick={() => { setAddingTag(false); setNewTag(''); }} aria-label="Cancel tag" title="Cancel"><Icon name="close" size={15} /></button>
          </form>
        ) : (
          <button className="add-tag-button" type="button" onClick={() => setAddingTag(true)}><Icon name="tag" size={14} />Add tag</button>
        )}
      </div>
    </div>
  );
}
