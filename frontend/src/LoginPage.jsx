import { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Mail, Lock, User, ArrowRight, Sparkles } from 'lucide-react';

export default function LoginPage() {
    const { login, register } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            if (isLogin) {
                await login(email, password);
            } else {
                await register(email, password, name);
            }
        } catch (err) {
            setError(err.message);
        }
        setLoading(false);
    };

    return (
        <div className="login-page">
            {/* Animated gradient blob */}
            <div className="login-bg-blob" />

            <div className="login-card">
                <div className="login-header">
                    <div className="login-logo">
                        <Sparkles size={24} />
                        <span>SocialAI</span>
                    </div>
                    <p className="login-subtitle">
                        {isLogin ? 'Welcome back to your co-pilot' : 'Create your workspace'}
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    {!isLogin && (
                        <label className="login-field">
                            <User size={16} className="login-field-icon" />
                            <input
                                type="text"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                placeholder="Full name"
                                className="login-input"
                            />
                        </label>
                    )}

                    <label className="login-field">
                        <Mail size={16} className="login-field-icon" />
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="Email address"
                            required
                            className="login-input"
                        />
                    </label>

                    <label className="login-field">
                        <Lock size={16} className="login-field-icon" />
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="Password"
                            required
                            minLength={6}
                            className="login-input"
                        />
                    </label>

                    {error && <div className="login-error">{error}</div>}

                    <button type="submit" className="login-btn" disabled={loading}>
                        {loading ? 'Please wait…' : (
                            <>
                                {isLogin ? 'Sign In' : 'Create Account'}
                                <ArrowRight size={16} />
                            </>
                        )}
                    </button>
                </form>

                <div className="login-toggle">
                    {isLogin ? "Don't have an account?" : 'Already have an account?'}
                    <button
                        onClick={() => { setIsLogin(!isLogin); setError(''); }}
                        className="login-toggle-btn"
                    >
                        {isLogin ? 'Sign Up' : 'Sign In'}
                    </button>
                </div>
            </div>
        </div>
    );
}
