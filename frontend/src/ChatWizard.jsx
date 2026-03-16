import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './context/AuthContext';
import { Send, Bot, User, Upload, Plus, X, Loader2, Pin, Image as ImageIcon } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

const ChatWizard = ({ pinnedImage, setPinnedImage, onRefresh, uploadMedia, cloudinaryAssets, messages, setMessages, input, setInput, onEditDraft, setDrafts }) => {
    const [isThinking, setIsThinking] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [currentStatus, setCurrentStatus] = useState('');

    const chatEndRef = useRef(null);
    const fileInputRef = useRef(null);

    const { authFetch } = useAuth();

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const addMsg = (role, text, extra = {}) => {
        setMessages(prev => [...prev, { role, text, ...extra }]);
    };

    const handleSend = async () => {
        const text = input.trim();
        if (!text || isThinking) return;
        setInput('');

        let contextMsg = text;
        if (pinnedImage) {
            contextMsg = `[Pinned Image: "${pinnedImage.name}" — ${pinnedImage.url}] ${text}`;
        }

        addMsg('user', text, pinnedImage ? { attachment: { name: pinnedImage.name, url: pinnedImage.url } } : {});
        setIsThinking(true);

        try {
            const response = await authFetch('/ai/chat', {
                method: 'POST',
                body: JSON.stringify({ message: contextMsg })
            });

            if (!response.ok) throw new Error('Server returned 500');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedData = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                accumulatedData += chunk;

                const lines = accumulatedData.split('\n');
                accumulatedData = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const json = JSON.parse(line.substring(6));
                            if (json.status) {
                                setCurrentStatus(json.status);
                            } else if (json.error) {
                                addMsg('assistant', `Error: ${json.error}`);
                            } else if (json.message) {
                                const reply = json.message;
                                const action = json.action;
                                const draft = json.draft_preview;

                                if (draft) {
                                    if (draft.row_index && setDrafts) {
                                        setDrafts(prev => {
                                            if (prev.some(d => String(d.row_index) === String(draft.row_index))) return prev;
                                            return [{
                                                topic: draft.topic,
                                                ig_caption: draft.caption || reply,
                                                fb_caption: draft.caption || reply,
                                                li_caption: draft.caption || reply,
                                                x_caption: draft.caption || reply,
                                                reel_url: draft.reel_url || pinnedImage?.url || null,
                                                row_index: draft.row_index,
                                                status: 'Draft'
                                            }, ...prev];
                                        });
                                    }

                                    addMsg('assistant', reply, {
                                        approvalCard: {
                                            topic: draft.topic || 'New Post',
                                            caption: draft.caption || reply,
                                            image: draft.reel_url || pinnedImage?.url || null,
                                            row_index: draft.row_index
                                        }
                                    });
                                } else {
                                    addMsg('assistant', reply);
                                }
                            }
                        } catch (err) {
                            console.error("Parse error in stream:", err, line);
                        }
                    }
                }
            }
        } catch (e) {
            addMsg('assistant', 'Sorry, something went wrong. The server may be overloaded. Please try again.');
        } finally {
            setIsThinking(false);
            setCurrentStatus('');
        }
    };

    const handleApproveInChat = async (card) => {
        addMsg('user', '✅ Approved! Publish now.');
        setIsThinking(true);
        try {
            if (card.row_index) {
                await axios.post(`${API_BASE}/workflow/approve-and-publish`, {
                    row_index: card.row_index,
                    platforms: 'ig,fb,li,rd',
                    schedule_time: 'now'
                });
                addMsg('assistant', '🚀 Published successfully to all platforms!');
            } else {
                addMsg('assistant', 'Draft created. Check Media Vision Lab to approve and publish.');
            }
            onRefresh();
        } catch (e) {
            addMsg('assistant', `Publish failed: ${e.response?.data?.detail || e.message}`);
        } finally {
            setIsThinking(false);
        }
    };

    const handleFileUpload = async (file) => {
        setIsUploading(true);
        addMsg('user', `📎 Uploading ${file.name}...`);
        try {
            const result = await uploadMedia(file);
            const pinData = { name: file.name, url: result.url, public_id: result.public_id };
            setPinnedImage(pinData);
            addMsg('assistant', `✅ "${file.name}" uploaded and pinned!\n\n**Pro Tip:** Want me to do everything automatically? Just say something like *"Analyze this image and create a post"* and I'll research it, draft captions, and generate hashtags in one go!`);
        } catch (e) {
            addMsg('assistant', `❌ Upload failed: ${e.response?.data?.detail || e.message}`);
        } finally {
            setIsUploading(false);
        }
    };

    const onDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);

        const textData = e.dataTransfer.getData('text/plain');
        if (textData) {
            try {
                const asset = JSON.parse(textData);
                if (asset.url && asset.name) {
                    setPinnedImage({ name: asset.name, url: asset.url, public_id: asset.public_id || asset.id });
                    addMsg('assistant', `📌 "${asset.name}" pinned from your Media Library! What would you like to do with it?`);
                    return;
                }
            } catch (_) { /* Not JSON, it's a file drop */ }
        }

        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    };

    return (
        <div
            className={`chat-container ${isDragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            style={{ position: 'relative' }}
        >
            <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={(e) => { if (e.target.files[0]) handleFileUpload(e.target.files[0]); e.target.value = ''; }}
                accept="image/*,video/*"
            />

            {isDragging && (
                <div className="drop-overlay">
                    <Upload size={40} />
                    <span>Drop to upload & pin</span>
                </div>
            )}

            {/* Messages */}
            <div className="chat-messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`message-row ${msg.role}`}>
                        <div className="message-avatar">
                            {msg.role === 'assistant' ? <Bot size={14} /> : <User size={14} />}
                        </div>
                        <div className="message-bubble">
                            {msg.text}
                            {msg.attachment && (
                                <div className="msg-attachment">
                                    <a href={msg.attachment.url} target="_blank" rel="noopener noreferrer">
                                        <img src={msg.attachment.url} alt={msg.attachment.name} />
                                    </a>
                                </div>
                            )}
                            {msg.approvalCard && (
                                <div className="approval-card">
                                    {msg.approvalCard.image && (
                                        <a href={msg.approvalCard.image} target="_blank" rel="noopener noreferrer">
                                            <img className="preview-img" src={msg.approvalCard.image} alt="Preview" />
                                        </a>
                                    )}
                                    <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.4rem', color: 'var(--text-primary)' }}>{msg.approvalCard.topic}</div>
                                    <div className="caption-text">{msg.approvalCard.caption}</div>
                                    <div className="action-row">
                                        <button className="btn btn-sm btn-success" onClick={() => handleApproveInChat(msg.approvalCard)}>
                                            ✅ Approve & Publish
                                        </button>
                                        <button className="btn btn-sm btn-secondary" onClick={() => onEditDraft?.(msg.approvalCard.row_index)}>✏️ Edit</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {/* Thinking/Status State */}
                {isThinking && (
                    <div className="message-row assistant">
                        <div className="message-avatar">
                            <Bot size={14} />
                        </div>
                        <div className="message-bubble">
                            <div className="status-indicator">
                                <Loader2 size={14} className="animate-spin" />
                                <span>{currentStatus || 'SocialAI is thinking...'}</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={chatEndRef} />
            </div>

            {/* Input Controls */}
            <div className="chat-input-controls">
                {pinnedImage && (
                    <div className="pinned-bar">
                        <div className="pin-img-container">
                            <a href={pinnedImage.url} target="_blank" rel="noopener noreferrer">
                                <img className="pin-thumb" src={pinnedImage.url} alt="pinned" />
                            </a>
                            <button className="pin-dismiss-btn" onClick={() => setPinnedImage(null)} title="Dismiss image">
                                <X size={12} />
                            </button>
                        </div>
                    </div>
                )}

                <div className="chat-input-row">
                    <button
                        className="icon-btn"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                    >
                        {isUploading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                    </button>

                    <input
                        type="text"
                        placeholder={isUploading ? 'Uploading...' : 'Tell me what to research, create, or publish...'}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    />

                    <button
                        className="icon-btn primary"
                        onClick={handleSend}
                        disabled={isThinking || !input.trim()}
                    >
                        <Send size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatWizard;
