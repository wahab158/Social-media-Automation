import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Edit3, Eye, CheckCircle, X, ChevronDown, Sparkles, Send, AlertTriangle, Loader2, Image as ImageIcon } from 'lucide-react';

/* ------- Constants ------- */

const RATIO_OPTIONS = {
    instagram: [
        { key: 'instagram_square', label: '1:1 Square' },
        { key: 'instagram_portrait', label: '4:5 Portrait' },
        { key: 'instagram_story', label: '9:16 Story' },
    ],
    facebook: [{ key: 'facebook_landscape', label: '1.91:1 Landscape' }],
    linkedin: [{ key: 'linkedin_landscape', label: '1.91:1 Landscape' }],
    twitter: [{ key: 'twitter_landscape', label: '16:9 Landscape' }],
};

const RATIO_ASPECT = {
    original: 'auto',
    instagram_square: '1 / 1',
    instagram_portrait: '4 / 5',
    instagram_story: '9 / 16',
    facebook_landscape: '1.91 / 1',
    linkedin_landscape: '1.91 / 1',
    twitter_landscape: '16 / 9',
};

const CHAR_LIMITS = {
    instagram: 2200,
    facebook: 63206,
    linkedin: 3000,
    twitter: 280,
};

const PLATFORM_LABELS = {
    instagram: 'Instagram',
    facebook: 'Facebook',
    linkedin: 'LinkedIn',
    twitter: 'X / Twitter',
};

const API_BASE = 'http://localhost:8000/api';

/* ------- Main Component ------- */

export default function ApprovalCard({ item, onApprove, onReject, onRefresh, isHighlighted, onClearHighlight }) {
    const cardRef = useRef(null);
    const PLATFORMS = ['instagram', 'facebook', 'linkedin', 'twitter'];

    useEffect(() => {
        if (isHighlighted && cardRef.current) {
            cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const timer = setTimeout(() => {
                onClearHighlight?.();
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [isHighlighted, onClearHighlight]);

    const [activeTab, setActiveTab] = useState('instagram');
    const [editing, setEditing] = useState(false);

    useEffect(() => {
        if (isHighlighted) {
            setEditing(true);
        }
    }, [isHighlighted]);
    const [saving, setSaving] = useState(false);
    const [posting, setPosting] = useState(false);
    const [showModal, setShowModal] = useState(false);

    const [captions, setCaptions] = useState({
        instagram: item.ig_caption || '',
        facebook: item.fb_caption || '',
        linkedin: item.li_caption || '',
        twitter: item.x_caption || '',
    });

    const [selectedPlatforms, setSelectedPlatforms] = useState(
        item.platforms === 'all'
            ? [...PLATFORMS]
            : (item.platforms || '').split(',').map(p => p.trim()).filter(Boolean)
    );

    /* ---------- Transform / AI State ---------- */
    const [transforms, setTransforms] = useState({});
    const [aiRecs, setAiRecs] = useState({});
    const [selectedRatios, setSelectedRatios] = useState({
        // Default to original if we have an image, else fallback to platform specific defaults
        instagram: item.reel_url ? 'original' : 'instagram_square',
        facebook: item.reel_url ? 'original' : 'facebook_landscape',
        linkedin: item.reel_url ? 'original' : 'linkedin_landscape',
        twitter: item.reel_url ? 'original' : 'twitter_landscape',
    });
    const [analyzing, setAnalyzing] = useState(false);
    const [localMediaUrl, setLocalMediaUrl] = useState(item.reel_url);
    const [refineInstruction, setRefineInstruction] = useState('');
    const [refining, setRefining] = useState(false);

    /* Run analysis when the card mounts if reel_url is a Cloudinary image */
    useEffect(() => {
        if (item.reel_url && item.reel_url.includes('cloudinary')) {
            const publicId = extractPublicId(item.reel_url);
            if (publicId) analyzeExistingImage(publicId, item.reel_url);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [item.reel_url]);

    useEffect(() => {
        if (aiRecs && Object.keys(aiRecs).length) {
            const updated = { ...selectedRatios };
            PLATFORMS.forEach(p => {
                if (aiRecs[p]?.ratio) updated[p] = aiRecs[p].ratio;
            });
            setSelectedRatios(updated);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [aiRecs]);

    /* ---------- Helpers ---------- */

    function extractPublicId(url) {
        try {
            const parts = url.split('/upload/');
            if (parts.length < 2) return null;
            let raw = parts[1];
            // Strip transformation params (v1234/...)
            if (/^v\d+\//.test(raw)) raw = raw.replace(/^v\d+\//, '');
            // Strip extension
            return raw.replace(/\.[^/.]+$/, '');
        } catch { return null; }
    }

    async function analyzeExistingImage(publicId, originalUrl) {
        setAnalyzing(true);
        try {
            // Generate transforms from the public_id
            const tUrls = {};
            const specs = {
                instagram_square: { w: 1080, h: 1080 },
                instagram_portrait: { w: 1080, h: 1350 },
                instagram_story: { w: 1080, h: 1920 },
                facebook_landscape: { w: 1200, h: 630 },
                linkedin_landscape: { w: 1200, h: 627 },
                twitter_landscape: { w: 1600, h: 900 },
            };
            const base = originalUrl.split('/upload/')[0];
            for (const [key, s] of Object.entries(specs)) {
                tUrls[key] = `${base}/upload/c_fill,g_auto:subject,w_${s.w},h_${s.h},q_auto:best,f_auto/${publicId}`;
            }
            setTransforms(tUrls);

            // Call the retransform endpoint to confirm and call the AI recommender
            // We use the upload-and-analyze only for new uploads.
            // For existing images, build transforms client-side (faster).
        } catch (e) {
            console.error('Analyze existing image error:', e);
        }
        setAnalyzing(false);
    }

    async function handleRatioChange(platform, ratioKey) {
        setSelectedRatios(prev => ({ ...prev, [platform]: ratioKey }));

        if (ratioKey !== 'original' && !transforms[ratioKey]) {
            try {
                const publicId = extractPublicId(localMediaUrl);
                if (!publicId) return;
                const res = await axios.post(`${API_BASE}/media/retransform`, {
                    public_id: publicId, ratio_key: ratioKey
                });
                setTransforms(prev => ({ ...prev, [ratioKey]: res.data.url }));
            } catch (e) {
                console.error('Retransform error:', e);
            }
        }
    }

    function togglePlatform(p) {
        setSelectedPlatforms(prev =>
            prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
        );
    }

    async function handleMediaUpload(e) {
        const file = e.target.files[0];
        if (!file) return;
        setAnalyzing(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await axios.post(`${API_BASE}/media/upload-and-analyze`, formData);
            const data = res.data;
            if (data.success) {
                setLocalMediaUrl(data.original_url);
                setTransforms(data.transforms || {});
                setAiRecs(data.ai_recommendations || {});
            }
        } catch (e) {
            console.error('Upload error:', e);
            alert('Upload failed');
        }
        setAnalyzing(false);
    }

    async function handleRefine() {
        if (!refineInstruction.trim()) return;
        setRefining(true);
        try {
            const res = await axios.post(`${API_BASE}/media/refine-caption`, {
                caption: captions[activeTab],
                instruction: refineInstruction,
                platform: activeTab
            });
            if (res.data.success) {
                setCaptions(prev => ({ ...prev, [activeTab]: res.data.refined }));
                setRefineInstruction('');
            }
        } catch (e) {
            console.error('Refine error:', e);
            alert('AI Refinement failed: ' + (e.response?.data?.detail || e.message));
        }
        setRefining(false);
    }

    /* ---------- Save Edits ---------- */

    async function saveEdits() {
        setSaving(true);
        try {
            await axios.post(`${API_BASE}/content/edit`, {
                row_index: item.row_index,
                ig_caption: captions.instagram,
                fb_caption: captions.facebook,
                li_caption: captions.linkedin,
                x_caption: captions.twitter,
                platforms: selectedPlatforms.join(','),
                reel_url: localMediaUrl
            });
            setEditing(false);
            if (onRefresh) onRefresh();
        } catch (e) {
            alert('Save failed: ' + (e.response?.data?.detail || e.message));
        }
        setSaving(false);
    }

    /* ---------- Approve ---------- */

    async function handleApprove() {
        if (selectedPlatforms.length === 0) return;
        setPosting(true);
        try {
            await onApprove(item.row_index, selectedPlatforms.join(','));
        } catch (e) {
            alert('Publish error: ' + e.message);
        }
        setPosting(false);
    }

    /* ---------- Derived State ---------- */

    const hasMedia = !!localMediaUrl;
    const currentRatio = selectedRatios[activeTab];
    const currentImage = currentRatio === 'original' ? localMediaUrl : (transforms[currentRatio] || localMediaUrl || null);
    const currentRec = aiRecs[activeTab];
    const charLimit = CHAR_LIMITS[activeTab] || 9999;
    const charCount = (captions[activeTab] || '').length;
    const isOverLimit = charCount > charLimit;

    /* ---------- Render ---------- */

    return (
        <div 
            ref={cardRef}
            className={`approval-card-v2 ${isHighlighted ? 'highlighted' : ''}`}
        >
            {/* Header */}
            <div className="ac-header">
                <div className="ac-header-left">
                    <span className="ac-status-badge">Draft</span>
                    <h3 className="ac-title">{item.topic}</h3>
                </div>
                <button
                    className={`btn btn-sm ${editing ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => editing ? saveEdits() : setEditing(true)}
                    disabled={saving}
                >
                    {saving ? 'Saving…' : editing ? (
                        <><CheckCircle size={13} /> Save</>
                    ) : (
                        <><Edit3 size={13} /> Edit</>
                    )}
                </button>
            </div>

            <div className="ac-body three-cols">
                {/* LEFT: Media Preview */}
                <div className="ac-preview-col">
                    {/* Platform tabs */}
                    <div className="ac-platform-tabs">
                        {PLATFORMS.map(p => (
                            <button key={p}
                                className={`ac-ptab ${activeTab === p ? 'active' : ''}`}
                                onClick={() => setActiveTab(p)}
                            >
                                {PLATFORM_LABELS[p]}
                            </button>
                        ))}
                    </div>

                    {/* Image preview */}
                    <div
                        className={`ac-preview-box ${hasMedia && currentRatio === 'original' ? 'ac-preview-original' : ''}`}
                        style={{
                            aspectRatio: hasMedia ? (RATIO_ASPECT[currentRatio] || '1 / 1') : '16 / 9',
                            background: hasMedia && currentRatio === 'original' ? 'transparent' : ''
                        }}
                    >
                        {analyzing ? (
                            <div className="ac-preview-loading">
                                <Sparkles size={24} className="animate-spin" />
                                <span>Processing…</span>
                            </div>
                        ) : hasMedia && currentImage ? (
                            <div className="ac-preview-click-wrap" onClick={() => setShowModal(true)} style={{ cursor: 'pointer', display: 'contents' }}>
                                <img src={currentImage} alt="Preview" style={currentRatio === 'original' ? { objectFit: 'contain', maxHeight: '400px', width: 'auto' } : {}} />
                                <div className="ac-preview-overlay-icon">
                                    <Eye size={24} color="white" />
                                </div>
                            </div>
                        ) : (
                            <div className="ac-preview-empty" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                                <input
                                    type="file"
                                    id={`upload-${item.row_index}`}
                                    style={{ display: 'none' }}
                                    accept="image/*"
                                    onChange={handleMediaUpload}
                                />
                                <label htmlFor={`upload-${item.row_index}`} className="btn btn-primary" style={{ cursor: 'pointer', padding: '1rem 2rem', fontSize: '1.2rem' }}>
                                    + Add Image
                                </label>
                                <span style={{ marginTop: '1rem', fontSize: '0.9rem' }}>Required for Instagram</span>
                            </div>
                        )}
                    </div>

                    {/* AI recommendation */}
                    {currentRec && (
                        <div className="ac-ai-rec">
                            <div className="ac-ai-rec-header">
                                <Sparkles size={12} />
                                <span className="ac-ai-rec-label">AI Recommendation</span>
                                <span className={`ac-confidence ${currentRec.confidence === 'High' ? 'high' : 'med'}`}>
                                    {currentRec.confidence}
                                </span>
                            </div>
                            <p className="ac-ai-rec-ratio">{currentRec.label}</p>
                            <p className="ac-ai-rec-reason">{currentRec.reason}</p>
                        </div>
                    )}

                    {/* Ratio override */}
                    {hasMedia && RATIO_OPTIONS[activeTab] && RATIO_OPTIONS[activeTab].length > 0 && (
                        <div className="ac-ratio-override">
                            <span className="ac-ratio-label">Crop Ratio</span>
                            <div className="ac-ratio-btns">
                                <button
                                    className={`ac-ratio-btn ${selectedRatios[activeTab] === 'original' ? 'active' : ''}`}
                                    onClick={() => handleRatioChange(activeTab, 'original')}
                                >
                                    Original
                                </button>
                                {RATIO_OPTIONS[activeTab].map(opt => (
                                    <button
                                        key={opt.key}
                                        className={`ac-ratio-btn ${selectedRatios[activeTab] === opt.key ? 'active' : ''}`}
                                        onClick={() => handleRatioChange(activeTab, opt.key)}
                                    >
                                        {opt.label}
                                        {aiRecs[activeTab]?.ratio === opt.key && (
                                            <span className="ac-ai-tag">AI</span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* MIDDLE: Caption Editor */}
                <div className="ac-editor-col">
                    {/* Caption area */}
                    <div className="ac-caption-section">
                        <div className="ac-caption-header">
                            <span>Caption for <strong>{PLATFORM_LABELS[activeTab]}</strong></span>
                        </div>

                        {editing ? (
                            <textarea
                                className={`ac-textarea ${isOverLimit ? 'over-limit' : ''}`}
                                value={captions[activeTab] || ''}
                                onChange={e => setCaptions(prev => ({ ...prev, [activeTab]: e.target.value }))}
                                rows={8}
                                placeholder={`Write your ${PLATFORM_LABELS[activeTab]} caption…`}
                            />
                        ) : (
                            <div
                                className="ac-caption-display"
                                onClick={() => setEditing(true)}
                                style={{ minHeight: '150px' }}
                            >
                                {captions[activeTab] || (
                                    <span className="ac-placeholder">Click Edit to write a caption</span>
                                )}
                            </div>
                        )}

                        <div className="ac-char-counter">
                            <span className="ac-char-hint">
                                {activeTab === 'twitter' ? 'Twitter enforces 280 char limit' : `Up to ${charLimit.toLocaleString()} chars`}
                            </span>
                            <span className={`ac-char-count ${isOverLimit ? 'over' : ''}`}>
                                {charCount} / {charLimit}
                            </span>
                        </div>
                    </div>

                    {/* AI Assistant */}
                    <div className="ac-ai-assistant" style={{ marginBottom: '1rem', background: 'var(--primary-muted)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-accent)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--primary)', fontSize: '0.85rem', fontWeight: 600 }}>
                            <Sparkles size={14} /> AI Caption Assistant
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <input
                                type="text"
                                className="input-text"
                                style={{ flex: 1, fontSize: '0.8rem', padding: '0.4rem 0.6rem' }}
                                placeholder="Instructions..."
                                value={refineInstruction}
                                onChange={(e) => setRefineInstruction(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleRefine()}
                            />
                            <button
                                className="btn btn-sm btn-primary"
                                onClick={handleRefine}
                                disabled={refining || !refineInstruction.trim()}
                                style={{ padding: '0 0.75rem' }}
                            >
                                {refining ? <Loader2 size={14} className="animate-spin" /> : 'Refine'}
                            </button>
                        </div>
                    </div>

                    {/* Quick switch */}
                    <div className="ac-other-captions">
                        <span className="ac-section-label">Switch Platform</span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                            {PLATFORMS.filter(p => p !== activeTab).map(p => (
                                <button key={p} className="btn btn-xs btn-ghost"
                                    onClick={() => { setActiveTab(p); }}
                                    style={{ fontSize: '0.7rem', border: '1px solid var(--border-subtle)' }}
                                >
                                    {PLATFORM_LABELS[p]}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* RIGHT: Platforms & Actions */}
                <div className="ac-platforms-col">
                    {/* Platform picker */}
                    <div className="ac-platform-picker-v2">
                        <span className="ac-section-label">Post To</span>
                        <div className="ac-check-list">
                            {PLATFORMS.map(p => (
                                <label key={p} className="ac-platform-check">
                                    <input
                                        type="checkbox"
                                        checked={selectedPlatforms.includes(p)}
                                        onChange={() => togglePlatform(p)}
                                    />
                                    <div className="ac-check-info">
                                        <span className="ac-check-label">{PLATFORM_LABELS[p]}</span>
                                        <span className="ac-check-ratio">
                                            {RATIO_OPTIONS[p]?.find(r => r.key === selectedRatios[p])?.label || 'Auto'}
                                        </span>
                                    </div>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="ac-side-actions">
                        <button
                            className="btn btn-sm btn-success ac-publish-btn"
                            style={{ width: '100%', marginBottom: '0.5rem' }}
                            onClick={handleApprove}
                            disabled={posting || selectedPlatforms.length === 0 || isOverLimit}
                        >
                            {posting ? <Loader2 size={14} className="animate-spin" /> : <>Publish <Send size={13} /></>}
                        </button>
                        <button
                            className="btn btn-sm btn-ghost"
                            style={{ width: '100%', color: 'var(--error)' }}
                            onClick={() => onReject(item.row_index)}
                        >
                            <X size={14} /> Reject Post
                        </button>
                    </div>

                    {isOverLimit && (
                        <div className="ac-overlimit-warn" style={{ marginTop: '1rem' }}>
                            <AlertTriangle size={13} />
                            <span>Over char limit</span>
                        </div>
                    )}
                </div>
            </div>

            {isOverLimit && (
                <div className="ac-overlimit-warn">
                    <AlertTriangle size={13} />
                    <span>{PLATFORM_LABELS[activeTab]} caption exceeds character limit</span>
                </div>
            )}

            {/* FULL SCREEN MODAL */}
            {showModal && (
                <div className="ac-modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="ac-modal-container" onClick={e => e.stopPropagation()}>
                        <button className="ac-modal-close" onClick={() => setShowModal(false)}>
                            <X size={20} />
                        </button>

                        <div className="ac-modal-preview-col">
                            <img
                                src={currentImage}
                                alt="Full Preview"
                                style={{
                                    aspectRatio: hasMedia ? (RATIO_ASPECT[currentRatio] || 'auto') : 'auto',
                                    objectFit: currentRatio === 'original' ? 'contain' : 'cover'
                                }}
                            />
                        </div>

                        <div className="ac-modal-sidebar">
                            <h2>Ratio Preview</h2>
                            <p>Select a platform ratio to see how your image will be cropped.</p>

                            <div className="ac-modal-ratio-group">
                                <span className="ac-modal-ratio-label">Default</span>
                                <div className="ac-modal-ratio-grid">
                                    <div
                                        className={`ac-modal-ratio-item ${currentRatio === 'original' ? 'active' : ''}`}
                                        onClick={() => handleRatioChange(activeTab, 'original')}
                                    >
                                        <div className="ac-modal-ratio-info">
                                            <span className="ac-modal-ratio-name">No Crop (Original)</span>
                                            <span className="ac-modal-ratio-desc">Show the image as uploaded</span>
                                        </div>
                                        <CheckCircle size={16} className="ac-modal-ratio-check" />
                                    </div>
                                </div>
                            </div>

                            <div className="ac-modal-ratio-group">
                                <span className="ac-modal-ratio-label">{PLATFORM_LABELS[activeTab]} Ratios</span>
                                <div className="ac-modal-ratio-grid">
                                    {RATIO_OPTIONS[activeTab]?.map(opt => (
                                        <div
                                            key={opt.key}
                                            className={`ac-modal-ratio-item ${currentRatio === opt.key ? 'active' : ''}`}
                                            onClick={() => handleRatioChange(activeTab, opt.key)}
                                        >
                                            <div className="ac-modal-ratio-info">
                                                <span className="ac-modal-ratio-name">{opt.label}</span>
                                                <span className="ac-modal-ratio-desc">
                                                    {opt.key.includes('square') ? '1:1 aspect ratio' :
                                                        opt.key.includes('portrait') ? '4:5 aspect ratio' :
                                                            opt.key.includes('story') ? '9:16 aspect ratio' : 'Wide aspect ratio'}
                                                </span>
                                            </div>
                                            <CheckCircle size={16} className="ac-modal-ratio-check" />
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div style={{ marginTop: 'auto' }}>
                                <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => setShowModal(false)}>
                                    Done
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
