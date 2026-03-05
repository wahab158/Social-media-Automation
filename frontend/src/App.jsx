import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LayoutDashboard,
  TrendingUp,
  Calendar,
  Settings,
  Video,
  CheckCircle,
  Send,
  Link as LinkIcon,
  Plus
} from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:8001/api';

function App() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const contentRes = await axios.get(`${API_BASE}/content/pending`);
      setItems(contentRes.data);
    } catch (error) {
      console.error("Error fetching content:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchVideos = async () => {
    try {
      const driveRes = await axios.get(`${API_BASE}/drive/videos`);
      setVideos(driveRes.data);
    } catch (error) {
      console.error("Error fetching videos:", error);
    }
  };

  const fetchData = async () => {
    await Promise.all([fetchItems(), fetchVideos()]);
  };

  const approvePost = async (row_index, platforms, schedule_time) => {
    try {
      await axios.post(`${API_BASE}/content/approve`, {
        row_index,
        status: 'Approved',
        platforms,
        schedule_time
      });
      fetchItems();
      alert("Post Approved Successfully!");
    } catch (error) {
      alert("Error approving post");
    }
  };

  const rejectPost = async (row_index) => {
    if (!window.confirm("Are you sure you want to reject this post?")) return;
    try {
      await axios.post(`${API_BASE}/content/approve`, {
        row_index,
        status: 'Rejected',
        platforms: '',
        schedule_time: ''
      });
      fetchItems();
      alert("Post Rejected.");
    } catch (error) {
      alert("Error rejecting post");
    }
  };

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">Antigravity Social</div>
        <nav>
          <a href="#" className="nav-item active"><LayoutDashboard size={20} /> Dashboard</a>
          <a href="#" className="nav-item"><TrendingUp size={20} /> Trends</a>
          <a href="#" className="nav-item"><Calendar size={20} /> Schedule</a>
          <a href="#" className="nav-item"><Settings size={20} /> Settings</a>
        </nav>
      </aside>

      {/* Main Area */}
      <main className="main-content">
        <header>
          <div>
            <h1>Content Queue</h1>
            <p style={{ color: 'var(--text-muted)' }}>Manage your AI-generated drafts</p>
          </div>
          <button className="btn btn-secondary" onClick={fetchData}>
            Refresh Data
          </button>
        </header>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '5rem' }}>
            <div className="loader"></div>
          </div>
        ) : (
          <div className="grid">
            {items.map((item) => (
              <ContentCard
                key={item.row_index}
                item={item}
                onApprove={approvePost}
                onReject={rejectPost}
              />
            ))}
            {items.length === 0 && (
              <div style={{ textAlign: 'center', gridColumn: '1/-1', padding: '5rem', color: 'var(--text-muted)' }}>
                No pending drafts. Run Module 2 to generate some!
              </div>
            )}
          </div>
        )}

        <section style={{ marginTop: '4rem' }}>
          <h2>Drive Assets</h2>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '1rem' }}>
            {videos.map(v => (
              <div key={v.id} className="card" style={{ width: '200px' }}>
                <Video size={32} color="var(--primary)" />
                <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>{v.name}</p>
                <a href={v.webViewLink} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ fontSize: '0.7rem', display: 'block', textAlign: 'center', marginTop: '0.5rem' }}>View</a>
              </div>
            ))}
            {videos.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No videos in specified Drive folder.</p>}
          </div>
        </section>
      </main>
    </div>
  );
}

function ContentCard({ item, onApprove, onReject }) {
  const [selectedPlatforms, setSelectedPlatforms] = useState(['fb', 'ig', 'li', 'x']);

  const togglePlatform = (p) => {
    if (selectedPlatforms.includes(p)) {
      setSelectedPlatforms(selectedPlatforms.filter(x => x !== p));
    } else {
      setSelectedPlatforms([...selectedPlatforms, p]);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <span className="tag">{item.status}</span>
        <div className="video-status">
          {item.reel_url ? <CheckCircle size={16} color="var(--success)" /> : <Plus size={16} />}
          {item.reel_url ? 'Video Linked' : 'No Video'}
        </div>
      </div>

      <h3 className="card-title">{item.topic}</h3>

      <div className="caption-preview">
        <strong>Instagram:</strong> {item.ig_caption}
      </div>

      <div className="platform-pills">
        {['fb', 'ig', 'li', 'x'].map(p => (
          <span
            key={p}
            className={`pill ${selectedPlatforms.includes(p) ? 'selected' : ''}`}
            onClick={() => togglePlatform(p)}
          >
            {p.toUpperCase()}
          </span>
        ))}
      </div>

      <div className="card-footer">
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary">Edit</button>
          <button className="btn btn-secondary" style={{ backgroundColor: '#ef4444', color: 'white' }} onClick={() => onReject(item.row_index)}>Deny</button>
          <a href={item.reel_url} target="_blank" rel="noreferrer" className="btn btn-secondary"><LinkIcon size={14} /></a>
        </div>
        <button
          className="btn btn-approve"
          onClick={() => onApprove(item.row_index, selectedPlatforms.join(','), 'now')}
        >
          Approve & Queue
        </button>
      </div>
    </div>
  );
}

export default App;
