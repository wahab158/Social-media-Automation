import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(() => sessionStorage.getItem('auth_token'));
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (token) {
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            // Validate token on mount
            fetch(`${API_BASE}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
                .then(r => r.ok ? r.json() : Promise.reject())
                .then(data => { setUser(data); setLoading(false); })
                .catch(() => {
                    setToken(null);
                    sessionStorage.removeItem('auth_token');
                    delete axios.defaults.headers.common['Authorization'];
                    setLoading(false);
                });
        } else {
            delete axios.defaults.headers.common['Authorization'];
            setLoading(false);
        }
    }, [token]);

    const login = async (email, password) => {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Login failed');
        setToken(data.token);
        sessionStorage.setItem('auth_token', data.token);
        setUser({ id: data.user_id, email: data.email });
        return data;
    };

    const register = async (email, password, name) => {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, name }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed');
        setToken(data.token);
        sessionStorage.setItem('auth_token', data.token);
        setUser({ id: data.user_id, email: data.email });
        return data;
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        sessionStorage.removeItem('auth_token');
        delete axios.defaults.headers.common['Authorization'];
    };

    const authFetch = (url, options = {}) => {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
        return fetch(fullUrl, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`,
                ...(options.body && typeof options.body === 'string'
                    ? { 'Content-Type': 'application/json' }
                    : {}),
            },
        });
    };

    return (
        <AuthContext.Provider value={{ user, token, loading, login, register, logout, authFetch }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
