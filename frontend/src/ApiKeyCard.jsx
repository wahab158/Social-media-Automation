import { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Shield, Check, X, AlertTriangle, Loader2 } from 'lucide-react';

export default function ApiKeyCard({ service, keyName, label, placeholder, helpText, onSaved }) {
    const { authFetch } = useAuth();
    const [value, setValue] = useState('');
    const [masked, setMasked] = useState(null);
    const [verified, setVerified] = useState(false);
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [status, setStatus] = useState(null);

    const handleSave = async () => {
        if (!value.trim()) return;
        setSaving(true);
        try {
            const res = await authFetch('/settings/keys', {
                method: 'POST',
                body: JSON.stringify({ service, key_name: keyName, value: value.trim() }),
            });
            if (res.ok) {
                setMasked(value.slice(0, 4) + '...' + value.slice(-6));
                setValue('');
                setVerified(false);
                setStatus(null);
                onSaved?.();
            }
        } catch (e) {
            setStatus({ success: false, message: e.message });
        }
        setSaving(false);
    };

    const handleTest = async () => {
        setTesting(true);
        setStatus(null);
        try {
            const res = await authFetch(`/settings/test/${service}`);
            const data = await res.json();
            setStatus({ success: data.success, message: data.message || data.error });
            if (data.success) setVerified(true);
        } catch (e) {
            setStatus({ success: false, message: e.message });
        }
        setTesting(false);
    };

    const handleDelete = async () => {
        try {
            await authFetch('/settings/keys', {
                method: 'DELETE',
                body: JSON.stringify({ service, key_name: keyName }),
            });
            setMasked(null);
            setVerified(false);
            setStatus(null);
        } catch (e) {
            setStatus({ success: false, message: e.message });
        }
    };

    return (
        <div className="akc-card">
            <div className="akc-header">
                <div className="akc-label-row">
                    <Shield size={14} className="akc-icon" />
                    <span className="akc-label">{label}</span>
                </div>
                {masked && (
                    <span className={`akc-badge ${verified ? 'verified' : 'saved'}`}>
                        {verified ? <><Check size={10} /> Verified</> : 'Saved'}
                    </span>
                )}
            </div>

            {helpText && <p className="akc-help">{helpText}</p>}

            {masked ? (
                <div className="akc-masked-row">
                    <code className="akc-masked-value">{masked}</code>
                    <button onClick={handleTest} disabled={testing} className="btn btn-sm btn-secondary">
                        {testing ? <><Loader2 size={13} className="animate-spin" /> Testing…</> : 'Test'}
                    </button>
                    <button onClick={handleDelete} className="btn btn-sm btn-danger">
                        Remove
                    </button>
                </div>
            ) : (
                <div className="akc-input-row">
                    <input
                        type="password"
                        value={value}
                        onChange={e => setValue(e.target.value)}
                        placeholder={placeholder}
                        className="akc-input"
                    />
                    <button onClick={handleSave} disabled={saving || !value.trim()} className="btn btn-sm btn-primary">
                        {saving ? 'Saving…' : 'Save'}
                    </button>
                </div>
            )}

            {status && (
                <div className={`akc-status ${status.success ? 'success' : 'error'}`}>
                    {status.success ? <Check size={13} /> : <AlertTriangle size={13} />}
                    <span>{status.message}</span>
                </div>
            )}
        </div>
    );
}
