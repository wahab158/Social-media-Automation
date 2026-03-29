import { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Mail, Lock, User, ArrowRight, Sparkles, Zap } from 'lucide-react';

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
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #10150d 0%, #1b1c18 40%, #262b23 100%)',
            fontFamily: "'Inter', sans-serif",
            position: 'relative',
            overflow: 'hidden',
        }}>
            {/* Animated gradient orbs */}
            <div style={{
                position: 'absolute',
                width: '600px',
                height: '600px',
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(96,108,56,0.15) 0%, transparent 70%)',
                top: '-200px',
                right: '-100px',
                animation: 'float 8s ease-in-out infinite',
            }} />
            <div style={{
                position: 'absolute',
                width: '400px',
                height: '400px',
                borderRadius: '50%',
                background: 'radial-gradient(circle, rgba(191,205,143,0.08) 0%, transparent 70%)',
                bottom: '-150px',
                left: '-50px',
                animation: 'float 10s ease-in-out infinite reverse',
            }} />

            <div style={{
                width: '100%',
                maxWidth: '420px',
                padding: '0 1.5rem',
                position: 'relative',
                zIndex: 10,
            }}>
                {/* Card */}
                <div style={{
                    background: 'rgba(28, 33, 25, 0.6)',
                    backdropFilter: 'blur(40px)',
                    WebkitBackdropFilter: 'blur(40px)',
                    border: '1px solid rgba(199, 200, 185, 0.08)',
                    borderRadius: '2rem',
                    padding: '3rem 2.5rem',
                    boxShadow: '0 25px 60px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)',
                }}>
                    {/* Logo */}
                    <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        marginBottom: '2.5rem',
                    }}>
                        <div style={{
                            width: '56px',
                            height: '56px',
                            borderRadius: '1rem',
                            background: 'linear-gradient(135deg, #606c38, #485422)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            marginBottom: '1.25rem',
                            boxShadow: '0 8px 25px rgba(96,108,56,0.3)',
                        }}>
                            <Zap size={26} color="#dbe9a9" fill="#dbe9a9" />
                        </div>
                        <h1 style={{
                            fontSize: '1.5rem',
                            fontWeight: 800,
                            color: '#dfe4d7',
                            letterSpacing: '-0.03em',
                            marginBottom: '0.35rem',
                        }}>
                            Curator AI
                        </h1>
                        <p style={{
                            fontSize: '0.85rem',
                            color: '#919284',
                            fontWeight: 500,
                        }}>
                            {isLogin ? 'Welcome back to your co-pilot' : 'Create your workspace'}
                        </p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {!isLogin && (
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                background: 'rgba(27, 28, 24, 0.6)',
                                border: '1px solid rgba(199, 200, 185, 0.08)',
                                borderRadius: '1rem',
                                padding: '0 1rem',
                                height: '52px',
                                transition: 'border-color 0.2s',
                            }}>
                                <User size={18} color="#919284" />
                                <input
                                    type="text"
                                    value={name}
                                    onChange={e => setName(e.target.value)}
                                    placeholder="Full name"
                                    style={{
                                        flex: 1,
                                        background: 'transparent',
                                        border: 'none',
                                        outline: 'none',
                                        fontSize: '0.9rem',
                                        color: '#dfe4d7',
                                        fontFamily: "'Inter', sans-serif",
                                    }}
                                />
                            </div>
                        )}

                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            background: 'rgba(27, 28, 24, 0.6)',
                            border: '1px solid rgba(199, 200, 185, 0.08)',
                            borderRadius: '1rem',
                            padding: '0 1rem',
                            height: '52px',
                        }}>
                            <Mail size={18} color="#919284" />
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="Email address"
                                required
                                style={{
                                    flex: 1,
                                    background: 'transparent',
                                    border: 'none',
                                    outline: 'none',
                                    fontSize: '0.9rem',
                                    color: '#dfe4d7',
                                    fontFamily: "'Inter', sans-serif",
                                }}
                            />
                        </div>

                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            background: 'rgba(27, 28, 24, 0.6)',
                            border: '1px solid rgba(199, 200, 185, 0.08)',
                            borderRadius: '1rem',
                            padding: '0 1rem',
                            height: '52px',
                        }}>
                            <Lock size={18} color="#919284" />
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="Password"
                                required
                                minLength={6}
                                style={{
                                    flex: 1,
                                    background: 'transparent',
                                    border: 'none',
                                    outline: 'none',
                                    fontSize: '0.9rem',
                                    color: '#dfe4d7',
                                    fontFamily: "'Inter', sans-serif",
                                }}
                            />
                        </div>

                        {error && (
                            <div style={{
                                background: 'rgba(186, 26, 26, 0.1)',
                                border: '1px solid rgba(186, 26, 26, 0.2)',
                                borderRadius: '0.75rem',
                                padding: '0.75rem 1rem',
                                fontSize: '0.8rem',
                                color: '#e57373',
                                fontWeight: 500,
                            }}>
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            style={{
                                width: '100%',
                                height: '52px',
                                borderRadius: '1rem',
                                border: 'none',
                                background: 'linear-gradient(135deg, #606c38, #485422)',
                                color: '#dbe9a9',
                                fontSize: '0.95rem',
                                fontWeight: 700,
                                fontFamily: "'Inter', sans-serif",
                                cursor: loading ? 'not-allowed' : 'pointer',
                                opacity: loading ? 0.6 : 1,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem',
                                marginTop: '0.5rem',
                                boxShadow: '0 8px 25px rgba(96,108,56,0.25)',
                                transition: 'all 0.3s cubic-bezier(0.25, 1, 0.5, 1)',
                                letterSpacing: '-0.01em',
                            }}
                            onMouseEnter={e => {
                                if (!loading) {
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                    e.currentTarget.style.boxShadow = '0 12px 35px rgba(96,108,56,0.35)';
                                }
                            }}
                            onMouseLeave={e => {
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = '0 8px 25px rgba(96,108,56,0.25)';
                            }}
                        >
                            {loading ? 'Please wait…' : (
                                <>
                                    {isLogin ? 'Sign In' : 'Create Account'}
                                    <ArrowRight size={18} />
                                </>
                            )}
                        </button>
                    </form>

                    {/* Toggle */}
                    <div style={{
                        textAlign: 'center',
                        marginTop: '2rem',
                        fontSize: '0.85rem',
                        color: '#919284',
                    }}>
                        {isLogin ? "Don't have an account?" : 'Already have an account?'}
                        {' '}
                        <button
                            onClick={() => { setIsLogin(!isLogin); setError(''); }}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: '#bfcd8f',
                                fontWeight: 700,
                                cursor: 'pointer',
                                fontFamily: "'Inter', sans-serif",
                                fontSize: '0.85rem',
                                textDecoration: 'none',
                                transition: 'color 0.2s',
                            }}
                            onMouseEnter={e => e.currentTarget.style.color = '#dbe9a9'}
                            onMouseLeave={e => e.currentTarget.style.color = '#bfcd8f'}
                        >
                            {isLogin ? 'Sign Up' : 'Sign In'}
                        </button>
                    </div>
                </div>

                {/* Bottom tagline */}
                <p style={{
                    textAlign: 'center',
                    marginTop: '2rem',
                    fontSize: '0.7rem',
                    color: 'rgba(145,146,132,0.4)',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.15em',
                }}>
                    AI-Powered Social Media Automation
                </p>
            </div>

            <style>{`
                @keyframes float {
                    0%, 100% { transform: translateY(0px) scale(1); }
                    50% { transform: translateY(-20px) scale(1.05); }
                }
                input::placeholder {
                    color: #6b6c60 !important;
                }
            `}</style>
        </div>
    );
}
