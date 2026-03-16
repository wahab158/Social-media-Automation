import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Radar, Eye, Image as ImageIcon, MessageSquare, Settings,
  Sparkles, Send, CheckCircle,
  Cloud, Upload, Trash2, Pin, X, RefreshCw, Loader2, LogOut, Newspaper, Search, CheckSquare,
  Sun, Moon, Menu, Zap, Layers
} from 'lucide-react';
import './App.css';
import ChatWizard from './ChatWizard';
import ApprovalCard from './ApprovalCard';
import { useAuth } from './context/AuthContext';
import LoginPage from './LoginPage';
import ApiKeyCard from './ApiKeyCard';

const API_BASE = 'http://localhost:8000/api';

/* ============================================
   MAIN APP
   ============================================ */
function App() {
  const { user, loading: authLoading, logout } = useAuth();
  const [view, setView] = useState('news');
  const [drafts, setDrafts] = useState([]);
  const [history, setHistory] = useState([]);
  const [media, setMedia] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [pinnedImage, setPinnedImage] = useState(null);

  // Persistence for AI Chat
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', text: "Hello! I'm your AI Social Media Co-Pilot. Upload or pin an image, then tell me what topic to research. I'll handle the rest!" }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [theme, setTheme] = useState(localStorage.getItem('social-ai-theme') || 'dark');
  const [accentTheme, setAccentTheme] = useState(localStorage.getItem('social-ai-accent') || 'olive');
  const [highlightedDraftId, setHighlightedDraftId] = useState(null);

  // Theme & Accent effect
  useEffect(() => {
    document.documentElement.className = theme;
    document.documentElement.setAttribute('data-accent', accentTheme);
    localStorage.setItem('social-ai-theme', theme);
    localStorage.setItem('social-ai-accent', accentTheme);
  }, [theme, accentTheme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const fetchDrafts = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/content/pending`);
      setDrafts(res.data);
    } catch (e) { console.error('Fetch drafts:', e); }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/content/history`);
      setHistory(res.data);
    } catch (e) { console.error('Fetch history:', e); }
  }, []);

  const fetchMedia = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/media/list`);
      setMedia(res.data.cloudinary || []);
    } catch (e) { console.error('Fetch media:', e); }
  }, []);

  const fetchNewsData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/news`);
      setNews(res.data);
    } catch (e) { console.error('Fetch news:', e); }
  }, []);

  const fetchAll = useCallback(async () => {
    if (!user) return;
    setSyncing(true);
    try {
      await Promise.all([fetchDrafts(), fetchHistory(), fetchMedia(), fetchNewsData()]);
    } catch (e) { console.error('Fetch all error:', e); }
    setSyncing(false);
    setLoading(false);
  }, [fetchDrafts, fetchHistory, fetchMedia, fetchNewsData, user]);

  useEffect(() => {
    if (user && !authLoading) {
      fetchAll();
    }
  }, [fetchAll, user, authLoading]);

  // Show login page if not authenticated
  if (authLoading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-base)' }}><div className="loader" /></div>;
  }
  if (!user) {
    return <LoginPage />;
  }

  const approvePost = async (row_index, platforms) => {
    setDrafts(prev => prev.filter(d => d.row_index !== row_index));
    try {
      await axios.post(`${API_BASE}/workflow/approve-and-publish`, {
        row_index, platforms, schedule_time: 'now'
      });
      fetchHistory();
    } catch (e) {
      alert('Publish error: ' + (e.response?.data?.detail || e.message));
      fetchDrafts();
    }
  };

  const rejectPost = async (row_index) => {
    if (!window.confirm('Reject this draft?')) return;
    setDrafts(prev => prev.filter(d => d.row_index !== row_index));
    try {
      await axios.post(`${API_BASE}/content/approve`, {
        row_index, status: 'Rejected', platforms: '', schedule_time: ''
      });
      fetchHistory(); // Refresh history tab since it's now Rejected
    } catch (e) {
      alert('Error rejecting: ' + (e.response?.data?.detail || e.message));
      fetchDrafts();
    }
  };

  const deleteHistoryItem = async (row_index) => {
    if (!window.confirm('Delete this item from history?')) return;
    setHistory(prev => prev.filter(item => item.row_index !== row_index));
    try {
      await axios.delete(`${API_BASE}/content/${row_index}`);
    } catch (e) {
      alert('Delete error: ' + (e.response?.data?.detail || e.message));
      fetchHistory();
    }
  };

  const deleteMediaAsset = async (public_id) => {
    if (!window.confirm('Delete this asset from Cloudinary?')) return;
    try {
      await axios.delete(`${API_BASE}/media/${encodeURIComponent(public_id)}`);
      fetchMedia();
      if (pinnedImage?.public_id === public_id) setPinnedImage(null);
    } catch (e) { alert('Delete error'); }
  };

  const uploadMedia = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post(`${API_BASE}/media/upload`, formData);
    fetchMedia();
    return res.data;
  };

  const skipNews = async (news_id) => {
    // Optimistic update: remove from local state immediately
    setNews(prev => prev.filter(n => n.news_id !== news_id));
    try {
      await axios.post(`${API_BASE}/news/skip`, { news_id });
      // We already filtered it out, but fetchNewsData will sync with DB if needed
      // Actually, if we don't call fetchNewsData, it's fine too as long as we don't refresh the whole page.
      // But let's call it to be sure we are in sync.
      fetchNewsData();
    } catch (e) { 
      alert('Skip error'); 
      fetchNewsData(); // Restore if failed
    }
  };

  const navItems = [
    { id: 'news', icon: Radar, label: 'News Radar', badge: news.filter(n => n.status === 'New').length > 0 },
    { id: 'approval', icon: Eye, label: 'Media Vision Lab' },
    { id: 'media', icon: ImageIcon, label: 'Media Gallery' },
    { id: 'ai-chat', icon: MessageSquare, label: 'AI Expert Chat' },
  ];

  const NavButton = ({ item, active, onClick }) => (
    <button 
      className={`nav-item ${active ? 'active' : ''}`} 
      onClick={onClick}
      data-nav={item.id}
    >
      <div className="nav-item-icon-wrapper">
        <item.icon size={20} />
      </div>
      <span>{item.label}</span>
      {item.badge && <span className="nav-item-badge" />}
    </button>
  );

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <Zap size={18} />
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">SocialAI</span>
            <span className="sidebar-brand-label">Agent</span>
          </div>
        </div>
        <nav>
          {navItems.map(n => (
            <NavButton key={n.id} item={n} active={view === n.id} onClick={() => setView(n.id)} />
          ))}
          <div className="nav-section-label">System</div>
          <NavButton 
            item={{ id: 'settings', icon: Settings, label: 'Settings' }} 
            active={view === 'settings'} 
            onClick={() => setView('settings')} 
          />
        </nav>
        <div className="sidebar-footer">
          <NavButton 
            item={{ id: 'logout', icon: LogOut, label: 'Sign Out' }} 
            active={false} 
            onClick={logout} 
          />
          <div className="sidebar-footer-info">
            <Sparkles size={12} /> Powered by AI
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Header Bar */}
        <div className="header-bar">
          <div className="admin-badge">
            <span className="admin-dot" />
            Admin
          </div>
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>

        <div className="page-body">
          {view === 'news' && (
            <NewsView
              news={news}
              onRefresh={fetchAll}
              syncing={syncing}
              onSkip={skipNews}
              setDrafts={setDrafts}
              setView={setView}
            />
          )}
          {view === 'approval' && (
            <ApprovalView
              drafts={drafts} history={history} loading={loading} syncing={syncing}
              onApprove={approvePost} onReject={rejectPost}
              onDeleteHistory={deleteHistoryItem}
              onRefresh={fetchAll} onRefreshHistory={fetchHistory}
              highlightedId={highlightedDraftId}
              onClearHighlight={() => setHighlightedDraftId(null)}
            />
          )}
          {view === 'media' && (
            <MediaView
              media={media} pinnedImage={pinnedImage}
              onPin={setPinnedImage} onDelete={deleteMediaAsset}
              onUpload={uploadMedia} onRefresh={fetchMedia}
              setView={setView}
            />
          )}
          {view === 'ai-chat' && (
            <ChatView
              pinnedImage={pinnedImage} setPinnedImage={setPinnedImage}
              onRefresh={fetchAll} uploadMedia={uploadMedia}
              media={media} setDrafts={setDrafts}
              messages={chatMessages} setMessages={setChatMessages}
              input={chatInput} setInput={setChatInput}
              onEditDraft={async (idx) => {
                // 1. Check if we already have it locally
                if (drafts.some(d => String(d.row_index) === String(idx))) {
                  setHighlightedDraftId(idx);
                  setView('approval');
                  return;
                }

                setSyncing(true);
                // Exponential backoff retry loop (up to 5 attempts)
                let found = false;
                let delay = 400;
                for (let attempt = 0; attempt < 5; attempt++) {
                  try {
                    const res = await axios.get(`${API_BASE}/content/pending`);
                    const latestDrafts = res.data;
                    
                    if (latestDrafts.some(d => String(d.row_index) === String(idx))) {
                      setDrafts(latestDrafts);
                      found = true;
                      break;
                    }
                  } catch (e) { console.error('Retry fetch drafts:', e); }
                  
                  console.log(`Draft ${idx} not found, retrying in ${delay}ms...`);
                  await new Promise(r => setTimeout(r, delay));
                  delay *= 2;
                }
                
                setHighlightedDraftId(idx);
                setView('approval');
                setSyncing(false);
                if (!found) console.warn(`Draft ${idx} not found after retries. It might appear in the next Sync.`);
              }}
            />
          )}
          {view === 'settings' && <SettingsView accentTheme={accentTheme} setAccentTheme={setAccentTheme} />}
        </div>
      </main>
    </div>
  );
}

/* ============================================
   VIEW — News Radar (Default)
   ============================================ */
function NewsView({ news, onRefresh, syncing, onSkip, setDrafts, setView }) {
  const [filter, setFilter] = useState('New');
  const [fetching, setFetching] = useState(false);
  const [fetchTopic, setFetchTopic] = useState('');
  const [fetchError, setFetchError] = useState('');
  const [selectedNews, setSelectedNews] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [editedSummaries, setEditedSummaries] = useState({});
  const [uploadingMedia, setUploadingMedia] = useState(null); // news_id being uploaded
  const [generatedNodes, setGeneratedNodes] = useState([]);

  const filteredNews = news.filter(n => filter === 'All' ? true : n.status === filter);

  const handleNewsImageUpload = async (newsId, file) => {
    setUploadingMedia(newsId);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await axios.post(`${API_BASE}/media/upload`, formData);
      const mediaUrl = res.data.url;
      
      // Save to news database immediately
      await axios.post(`${API_BASE}/news/edit`, {
        news_id: newsId,
        media_url: mediaUrl
      });
      onRefresh(); // Get the updated media_url
    } catch (e) {
      alert('Upload failed: ' + (e.response?.data?.detail || e.message));
    }
    setUploadingMedia(null);
  };

  const handleSaveNewsEdit = async (newsId) => {
    try {
      await axios.post(`${API_BASE}/news/edit`, {
        news_id: newsId,
        summary: editedSummaries[newsId]
      });
      alert('News item saved!');
      onRefresh();
    } catch (e) {
      alert('Save failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const toggleSelect = (id) => {
    setSelectedNews(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleFetch = async () => {
    setFetching(true);
    setFetchError('');
    try {
      const res = await axios.post(`${API_BASE}/news/fetch`, { topics: fetchTopic || null });
      alert(res.data.message);
      onRefresh();
    } catch (e) {
      setFetchError(e.response?.data?.detail || e.message);
    }
    setFetching(false);
  };

  const handleGenerate = async (newsIds) => {
    if (newsIds.length === 0) return;
    setGenerating(true);
    try {
      await axios.post(`${API_BASE}/news/generate`, { news_ids: newsIds });
      setGeneratedNodes(prev => [...prev, ...newsIds]);
      setSelectedNews([]);
      const draftsRes = await axios.get(`${API_BASE}/content/pending`);
      setDrafts(draftsRes.data);
      onRefresh();
      setView('approval');
    } catch (e) {
      alert('Generation error: ' + (e.response?.data?.detail || e.message));
    }
    setGenerating(false);
  };

  const handleCustomGenerate = async () => {
    if (!fetchTopic.trim()) {
      setFetchError('Please type some news content first to generate a custom post.');
      return;
    }
    setGenerating(true);
    setFetchError('');
    try {
      const res = await axios.post(`${API_BASE}/news/custom`, { text: fetchTopic });
      alert(res.data.message || 'Custom post generated!');
      setFetchTopic('');
      const draftsRes = await axios.get(`${API_BASE}/content/pending`);
      setDrafts(draftsRes.data);
      setView('approval');
    } catch (e) {
      setFetchError(e.response?.data?.detail || e.message);
    }
    setGenerating(false);
  };

  const handleSummaryEdit = (id, newText) => {
    setEditedSummaries(prev => ({ ...prev, [id]: newText }));
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 style={{ color: 'var(--theme-accent)', marginBottom: '0.25rem' }}>Social SaaS</h1>
          <p style={{ fontWeight: 600, opacity: 0.6 }}>Multi-Tenant Dashboard</p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh} disabled={syncing}>
          {syncing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />} Sync
        </button>
      </div>

      {/* Topic Control */}
      <div className="card" style={{ marginBottom: '2rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ flex: 1, minWidth: '350px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-muted)', fontSize: '1.1rem', fontWeight: 700 }}>
             <Search size={22} /> Topic Control
          </div>
          <div className="gemini-search-box" style={{ padding: '1rem 1.25rem' }}>
            <input
              type="text"
              placeholder="Search news by topic (e.g. AI) OR paste custom news text..."
              className="gemini-search-input"
              style={{ fontSize: '1.05rem' }}
              value={fetchTopic}
              onChange={(e) => setFetchTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleFetch()}
            />
            <div style={{ display: 'flex', gap: '0.75rem', marginLeft: '1rem', flexShrink: 0 }}>
              <button className="btn btn-secondary" onClick={handleCustomGenerate} disabled={generating || fetching}>
                {generating ? <><Loader2 size={16} className="animate-spin" /> Crafting...</> : <><Sparkles size={16} /> Craft Custom Post</>}
              </button>
              <button className="btn btn-primary" style={{ padding: '0.75rem 1.5rem' }} onClick={handleFetch} disabled={fetching || generating}>
                {fetching ? 'Fetching...' : 'Fetch Now'}
              </button>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', background: 'var(--bg-input)', padding: '0.4rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', alignSelf: 'center' }}>
          <button className={`btn btn-sm ${filter === 'New' ? 'btn-secondary' : 'btn-ghost'}`} onClick={() => setFilter('New')}>Unread Only</button>
          <button className={`btn btn-sm ${filter === 'All' ? 'btn-secondary' : 'btn-ghost'}`} onClick={() => setFilter('All')}>Show All</button>
        </div>
      </div>

      {fetchError && (
        <div style={{ marginBottom: '1.5rem', padding: '0.75rem 1rem', background: 'var(--error-bg)', border: '1px solid var(--error)', color: 'var(--error)', borderRadius: 'var(--radius-md)', fontSize: '0.85rem' }}>
          <strong>Error: </strong>{fetchError}
        </div>
      )}

      {/* Bulk Toolbar */}
      {selectedNews.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--gradient-accent)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', color: 'white' }}>
          <span><strong>{selectedNews.length}</strong> articles selected</span>
          <button className="btn btn-sm" style={{ background: 'white', color: 'var(--primary)' }} onClick={() => handleGenerate(selectedNews)} disabled={generating}>
            {generating ? <><Loader2 size={14} className="animate-spin" /> Generating...</> : <><Layers size={14} /> Generate Posts</>}
          </button>
        </div>
      )}

      <div className="news-grid" style={{ gridTemplateColumns: '1fr', gap: '2rem' }}>
        {filteredNews.map(item => {
          const isSelected = selectedNews.includes(item.news_id);
          const isGenerated = generatedNodes.includes(item.news_id) || item.status === 'Used';

          return (
            <div key={item.news_id} className={`card ${isSelected ? 'selected-card' : ''}`}>
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input type="checkbox" checked={isSelected} onChange={() => toggleSelect(item.news_id)} style={{ accentColor: 'var(--primary)' }} />
                  <span className="tag tag-secondary">{item.source_name || 'Unknown'}</span>
                  {item.relevance_score && <span className="tag tag-primary">{item.relevance_score}</span>}
                </div>
                {item.status !== 'New' && <span className="tag tag-secondary">{item.status}</span>}
              </div>

              <h3 style={{ fontSize: '0.95rem', marginBottom: '0.5rem', lineHeight: 1.4, color: 'var(--text-primary)', fontWeight: 600 }}>{item.title}</h3>
              

              {isGenerated ? (
                <p style={{ 
                  fontSize: '0.82rem', 
                  color: 'var(--text-muted)', 
                  marginBottom: '1rem', 
                  display: '-webkit-box', 
                  WebkitLineClamp: 20, 
                  WebkitBoxOrient: 'vertical', 
                  overflow: 'hidden', 
                  lineClamp: 20,
                  lineHeight: '1.5'
                }}>
                  {editedSummaries[item.news_id] !== undefined ? editedSummaries[item.news_id] : item.summary}
                </p>
              ) : (
                <textarea
                  className="input-text"
                  style={{
                    width: '100%',
                    minHeight: '80px',
                    resize: 'vertical',
                    marginBottom: '1rem',
                    lineHeight: '1.5',
                    fontSize: '0.82rem',
                    padding: '0.5rem'
                  }}
                  value={editedSummaries[item.news_id] !== undefined ? editedSummaries[item.news_id] : item.summary}
                  onChange={(e) => handleSummaryEdit(item.news_id, e.target.value)}
                  placeholder="Edit summary..."
                />
              )}

              <div className="card-footer">
                {!isGenerated ? (
                  <>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button className="btn btn-sm btn-secondary" onClick={() => onSkip(item.news_id)} title="Skip">
                        <X size={14} />
                      </button>
                      {editedSummaries[item.news_id] !== undefined && (
                        <button className="btn btn-sm btn-secondary" onClick={() => handleSaveNewsEdit(item.news_id)} title="Save Changes">
                          <CheckCircle size={14} />
                        </button>
                      )}
                    </div>
                    <button className="btn btn-sm btn-primary" onClick={() => handleGenerate([item.news_id])} disabled={generating}>
                      Generate <Sparkles size={12} />
                    </button>
                  </>
                ) : (
                  <span style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.82rem', fontWeight: 600 }}>
                    <CheckCircle size={14} /> Draft Created
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {filteredNews.length === 0 && (
          <div className="empty-state" style={{ gridColumn: '1/-1' }}>
            <Newspaper size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
            <p>No {filter === 'New' ? 'unread' : 'saved'} news found. Try fetching some topics!</p>
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================
   VIEW — Media Vision Lab (Approval + History)
   ============================================ */
function ApprovalView({ drafts, history, loading, syncing, onApprove, onReject, onDeleteHistory, onRefresh, onRefreshHistory, highlightedId, onClearHighlight }) {
  const [tab, setTab] = useState('drafts');

  useEffect(() => {
    if (highlightedId) setTab('drafts');
  }, [highlightedId]);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Media Vision Lab</h1>
          <p>Review, edit & publish your AI-generated content</p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh} disabled={syncing}>
          {syncing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />} Sync
        </button>
      </div>

      {/* Tab Toggle */}
      <div style={{ display: 'flex', gap: '0.25rem', background: 'var(--bg-card)', padding: '0.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', marginBottom: '1.5rem', width: 'fit-content' }}>
        <button className={`btn btn-sm ${tab === 'drafts' ? 'btn-secondary' : 'btn-ghost'}`} onClick={() => setTab('drafts')}>
          Pending Drafts <span className="tag tag-primary" style={{ marginLeft: '0.35rem' }}>{drafts.length}</span>
        </button>
        <button className={`btn btn-sm ${tab === 'history' ? 'btn-secondary' : 'btn-ghost'}`} onClick={() => setTab('history')}>
          Post History
        </button>
      </div>

      {tab === 'drafts' && (
        <>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}><div className="loader" /></div>
          ) : drafts.length === 0 ? (
            <div className="empty-state">
              <Eye size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p>No pending drafts. Go to <strong>News Radar</strong> to generate content!</p>
            </div>
          ) : (
            <div className="approval-grid">
              {drafts.map(item => (
                <ApprovalCard
                  key={item.row_index}
                  item={item}
                  onApprove={onApprove}
                  onReject={onReject}
                  onRefresh={onRefresh}
                  isHighlighted={highlightedId === item.row_index}
                  onClearHighlight={onClearHighlight}
                />
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'history' && (
        <>
          {history.length === 0 ? (
            <div className="empty-state">
              <Layers size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p>No post history yet. Approve a draft to see it here!</p>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Topic</th>
                    <th>Status</th>
                    <th>Platforms</th>
                    <th>Posted At</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(item => (
                    <tr key={item.row_index}>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500, maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.topic}
                      </td>
                      <td>
                        <span className={`tag ${item.status === 'Posted' ? 'tag-success' : 'tag-error'}`}>{item.status}</span>
                      </td>
                      <td style={{ fontSize: '0.82rem' }}>{item.platforms}</td>
                      <td style={{ fontSize: '0.82rem' }}>{item.posted_at || '—'}</td>
                      <td>
                        <button className="btn btn-sm btn-danger" onClick={() => onDeleteHistory(item.row_index)}>
                          <Trash2 size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  );
}

/* ============================================
   VIEW — AI Expert Chat
   ============================================ */
function ChatView({ pinnedImage, setPinnedImage, onRefresh, uploadMedia, media, messages, setMessages, input, setInput, onEditDraft, setDrafts }) {
  return (
    <>
      <div className="page-header">
        <div>
          <h1>AI Expert Chat</h1>
          <p>Research, create & publish — all from one conversation</p>
        </div>
      </div>
      <ChatWizard
        pinnedImage={pinnedImage}
        setPinnedImage={setPinnedImage}
        onRefresh={onRefresh}
        uploadMedia={uploadMedia}
        cloudinaryAssets={media}
        messages={messages}
        setMessages={setMessages}
        input={input}
        setInput={setInput}
        onEditDraft={onEditDraft}
        setDrafts={setDrafts}
      />
    </>
  );
}

/* ============================================
   VIEW — Media Gallery
   ============================================ */
function MediaView({ media, pinnedImage, onPin, onDelete, onUpload, onRefresh, setView }) {
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const handleUpload = async (files) => {
    setUploading(true);
    try {
      for (const f of files) {
        if (f.type.startsWith('image/')) {
          const formData = new FormData();
          formData.append('file', f);
          await axios.post(`${API_BASE}/media/upload-and-analyze`, formData);
        } else {
          await onUpload(f);
        }
      }
      onRefresh();
    } catch (e) { alert('Upload failed: ' + e.message); }
    setUploading(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) handleUpload(Array.from(e.dataTransfer.files));
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Media Gallery</h1>
          <p>Upload & manage your Cloudinary assets</p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh}><RefreshCw size={16} /> Refresh</button>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById('media-upload-input').click()}
      >
        <input
          id="media-upload-input"
          type="file"
          multiple
          accept="image/*,video/*"
          style={{ display: 'none' }}
          onChange={(e) => handleUpload(Array.from(e.target.files))}
        />
        {uploading ? (
          <><Loader2 size={32} className="animate-spin" /><p style={{ marginTop: '0.5rem' }}>Uploading & analyzing...</p></>
        ) : (
          <><Upload size={32} /><p style={{ marginTop: '0.5rem' }}>Drop files here or click to upload</p></>
        )}
      </div>

      {pinnedImage && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--primary-muted)', border: '1px solid var(--border-accent)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Pin size={14} color="var(--primary)" />
          <img src={pinnedImage.url} alt="" style={{ width: 32, height: 32, borderRadius: 4, objectFit: 'cover' }} />
          <span style={{ fontSize: '0.82rem', color: 'var(--primary)', flex: 1 }}>
            <strong>{pinnedImage.name}</strong> is pinned for AI Chat
          </span>
          <button className="btn btn-sm btn-secondary" onClick={() => setView('ai-chat')}>Go to Chat →</button>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => onPin(null)}><X size={16} /></button>
        </div>
      )}

      {/* Grid */}
      <div className="media-grid">
        {media.map(asset => (
          <div key={asset.id} className={`media-asset ${pinnedImage?.public_id === asset.id ? 'pinned' : ''}`}>
            {pinnedImage?.public_id === asset.id && <div className="pin-badge">PINNED</div>}
            {asset.resource_type === 'image' ? (
              <img src={asset.url} alt={asset.name} loading="lazy" />
            ) : (
              <video src={asset.url} muted />
            )}
            <div className="media-asset-info">
              <div className="name">{asset.name}</div>
              <div className="meta">{asset.resource_type} • {asset.format}</div>
            </div>
            <div className="media-asset-actions">
              <button
                className="btn btn-sm btn-primary"
                onClick={() => onPin({ name: asset.name, url: asset.url, public_id: asset.id })}
              >
                <Pin size={12} /> Pin for AI
              </button>
              <button className="btn btn-sm btn-danger" onClick={() => onDelete(asset.id)}>
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))}
        {media.length === 0 && (
          <div className="empty-state" style={{ gridColumn: '1/-1' }}>
            <Cloud size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
            <p>No assets yet. Upload images above to get started!</p>
          </div>
        )}
      </div>
    </>
  );
}

/* ============================================
   VIEW — Settings
   ============================================ */
function SettingsView({ accentTheme, setAccentTheme }) {
  const SECTIONS = ['Appearance', 'AI Provider', 'Social Publishing', 'News Sources', 'News Preferences', 'Media Storage', 'Google Sheets'];
  const [active, setActive] = useState('Appearance');
  const [prefs, setPrefs] = useState({ topics: '', post_time: '07:00', is_enabled: 1 });
  const [savingPrefs, setSavingPrefs] = useState(false);

  useEffect(() => {
    if (active === 'News Preferences') {
      axios.get(`${API_BASE}/settings`).then(res => {
        if (res.data.preferences) {
          setPrefs({
            topics: res.data.preferences.topics || '',
            post_time: res.data.preferences.post_time || '07:00',
            is_enabled: res.data.preferences.is_enabled !== undefined ? res.data.preferences.is_enabled : 1
          });
        }
      }).catch(console.error);
    }
  }, [active]);

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      await axios.post(`${API_BASE}/settings/preferences`, prefs);
    } catch (e) {
      alert('Failed to save preferences');
    }
    setSavingPrefs(false);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Configure your API keys, integrations & preferences</p>
        </div>
      </div>

      <div className="settings-layout">
        <div className="settings-nav">
          {SECTIONS.map(s => (
            <button key={s}
              className={`settings-nav-item ${active === s ? 'active' : ''}`}
              onClick={() => setActive(s)}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="settings-panel">
          {active === 'Appearance' && (
            <div className="settings-section">
              <h2>Appearance</h2>
              <p className="settings-desc">Customize the look and feel of your dashboard.</p>
              
              <div className="akc-card">
                <div className="akc-label" style={{ marginBottom: '1rem' }}>Accent Theme</div>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  {[
                    { id: 'olive', color: 'hsl(45, 45%, 38%)', label: 'Olive' },
                    { id: 'burgundy', color: 'hsl(0, 40%, 38%)', label: 'Burgundy' },
                    { id: 'slate', color: 'hsl(210, 20%, 42%)', label: 'Slate' },
                    { id: 'forest', color: 'hsl(150, 35%, 35%)', label: 'Forest' },
                    { id: 'terracotta', color: 'hsl(16, 50%, 45%)', label: 'Terracotta' },
                  ].map(t => (
                    <button
                      key={t.id}
                      onClick={() => setAccentTheme(t.id)}
                      style={{
                        padding: '0.75rem',
                        borderRadius: '12px',
                        border: accentTheme === t.id ? '2px solid var(--text-primary)' : '2px solid transparent',
                        background: 'var(--bg-card-hover)',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '0.5rem',
                        minWidth: '80px',
                        transition: 'all 0.2s'
                      }}
                    >
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: t.color }} />
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {active === 'AI Provider' && (
            <div className="settings-section">
              <h2>AI Provider</h2>
              <p className="settings-desc">Used for content generation and chat. Pick one provider and paste your key.</p>
              <ApiKeyCard service="openai" keyName="api_key" label="OpenAI API Key" placeholder="sk-..." helpText="Get your key at platform.openai.com/api-keys" />
              <ApiKeyCard service="groq" keyName="api_key" label="Groq API Key" placeholder="gsk_..." helpText="Get your key at console.groq.com" />
            </div>
          )}

          {active === 'Social Publishing' && (
            <div className="settings-section">
              <h2>Social Publishing (Ayrshare)</h2>
              <p className="settings-desc">Connect your Ayrshare key to publish to Instagram, Facebook, LinkedIn, and X.</p>
              <ApiKeyCard service="ayrshare" keyName="api_key" label="Ayrshare API Key" placeholder="AY-..." helpText="Get your key at app.ayrshare.com" />
            </div>
          )}

          {active === 'News Sources' && (
            <div className="settings-section">
              <h2>News Sources</h2>
              <p className="settings-desc">Enable one or more sources. The pipeline fetches from all active sources.</p>
              <ApiKeyCard service="newsapi" keyName="api_key" label="NewsAPI Key" placeholder="na_..." helpText="Free tier at newsapi.org (100 req/day)" />
              <ApiKeyCard service="tavily" keyName="api_key" label="Tavily API Key" placeholder="tvly-..." helpText="AI-powered search at tavily.com" />
            </div>
          )}

          {active === 'News Preferences' && (
            <div className="settings-section">
              <h2>News Preferences</h2>
              <p className="settings-desc">Configure the daily automated background fetcher.</p>
 
              <div className="akc-card">
                <div className="akc-header" style={{ marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <div className="akc-label">Enable Automated News</div>
                    <button 
                      className={`btn btn-sm ${prefs.is_enabled ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setPrefs({ ...prefs, is_enabled: prefs.is_enabled ? 0 : 1 })}
                    >
                      {prefs.is_enabled ? 'ON' : 'OFF'}
                    </button>
                  </div>
                </div>
                <div className="akc-help" style={{ marginTop: '-0.25rem' }}>If enabled, the system will automatically fetch news based on the schedule below.</div>
              </div>

              <div className="akc-card">
                <div className="akc-header" style={{ marginBottom: '0.75rem' }}>
                  <div className="akc-label-row">
                    <div className="akc-label">Daily Topic Watchlist</div>
                  </div>
                </div>
                <div className="akc-help" style={{ marginTop: '-0.5rem', marginBottom: '1rem' }}>Comma-separated topics (e.g. AI, Space, Economy)</div>
                <div className="akc-input-row">
                  <input
                    type="text"
                    className="akc-input"
                    value={prefs.topics}
                    onChange={(e) => setPrefs({ ...prefs, topics: e.target.value })}
                    placeholder="e.g. AI, Startups"
                  />
                </div>
              </div>

              <div className="akc-card">
                <div className="akc-header" style={{ marginBottom: '0.75rem' }}>
                  <div className="akc-label-row">
                    <div className="akc-label">Daily Schedule Time</div>
                  </div>
                </div>
                <div className="akc-help" style={{ marginTop: '-0.5rem', marginBottom: '1rem' }}>Set the time (24h) for the daily automatic news fetch</div>
                <div className="akc-input-row">
                  <input
                    type="time"
                    className="akc-input"
                    value={prefs.post_time}
                    onChange={(e) => setPrefs({ ...prefs, post_time: e.target.value })}
                  />
                </div>
              </div>

              <button className="btn btn-primary" onClick={savePreferences} disabled={savingPrefs} style={{ marginTop: '0.5rem' }}>
                {savingPrefs ? 'Saving…' : 'Save Preferences'}
              </button>
            </div>
          )}

          {active === 'Media Storage' && (
            <div className="settings-section">
              <h2>Media Storage (Cloudinary)</h2>
              <p className="settings-desc">Configure Cloudinary for image hosting and AI transforms.</p>
              <ApiKeyCard service="cloudinary" keyName="cloud_name" label="Cloud Name" placeholder="your-cloud-name" helpText="Found at cloudinary.com/console" />
              <ApiKeyCard service="cloudinary" keyName="api_key" label="API Key" placeholder="123456789" />
              <ApiKeyCard service="cloudinary" keyName="api_secret" label="API Secret" placeholder="AbCdEf..." />
            </div>
          )}

          {active === 'Google Sheets' && (
            <div className="settings-section">
              <h2>Google Sheets</h2>
              <p className="settings-desc">Configure the Google Sheets connection for content & news storage.</p>
              <ApiKeyCard service="sheets" keyName="spreadsheet_id" label="Spreadsheet ID" placeholder="1abc...xyz" helpText="Found in the Google Sheets URL" />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default App;
