import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, Bot, User, Sparkles } from 'lucide-react';

const API_BASE = 'http://localhost:8001/api';

const ChatWizard = ({ onRefresh }) => {
    const [messages, setMessages] = useState([
        { role: 'assistant', text: 'Hello! I am your AI Social Media Manager. How can I help you today? You can ask me to research news, generate drafts, or publish posts.' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const chatEndRef = useRef(null);

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage = { role: 'user', text: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await axios.post(`${API_BASE}/ai/chat`, { message: input });
            const aiMessage = { role: 'assistant', text: response.data.response };
            setMessages(prev => [...prev, aiMessage]);

            // If a tool was called that might change the dashboard state, refresh it
            if (response.data.intent && response.data.intent.action !== 'chat') {
                setTimeout(onRefresh, 2000); // Wait a bit for side effects
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', text: 'Sorry, I encountered an error processing that request.' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-wizard card">
            <div className="chat-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div className="ai-status-pulse"></div>
                    <Sparkles size={18} color="var(--primary)" />
                    <strong>AI Command Center</strong>
                </div>
            </div>

            <div className="chat-messages">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message-wrapper ${msg.role}`}>
                        <div className="message-icon">
                            {msg.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}
                        </div>
                        <div className="message-text">
                            {msg.text}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="message-wrapper assistant">
                        <div className="message-icon"><Bot size={16} /></div>
                        <div className="message-text loading">
                            <span className="dot"></span><span className="dot"></span><span className="dot"></span>
                        </div>
                    </div>
                )}
                <div ref={chatEndRef} />
            </div>

            <div className="chat-input-area">
                <input
                    type="text"
                    placeholder="Ask me to research, generate, or publish..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                />
                <button className="chat-send-btn" onClick={handleSend} disabled={loading}>
                    <Send size={18} />
                </button>
            </div>
        </div>
    );
};

export default ChatWizard;
