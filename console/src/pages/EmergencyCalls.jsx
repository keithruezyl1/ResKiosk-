import React, { useState, useEffect, useCallback } from 'react';
import hubClient from '../api/hubClient';
import { RefreshCw, Phone } from 'lucide-react';

function EmergencyCalls() {
    const [alerts, setAlerts] = useState([]);
    const [kiosks, setKiosks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingKiosk, setEditingKiosk] = useState(null);
    const [editName, setEditName] = useState('');

    const fetchActive = useCallback(async () => {
        try {
            const res = await hubClient.get('/emergency/active');
            setAlerts(res.data.alerts || []);
        } catch (e) {
            console.error(e);
        }
    }, []);

    const fetchNetwork = useCallback(async () => {
        try {
            const res = await hubClient.get('/network/info');
            setKiosks(res.data.kiosks_list || []);
        } catch (e) {
            console.error(e);
        }
    }, []);

    const load = useCallback(async () => {
        setLoading(true);
        await Promise.all([fetchActive(), fetchNetwork()]);
        setLoading(false);
    }, [fetchActive, fetchNetwork]);

    useEffect(() => {
        load();
    }, [load]);

    // SSE for new alerts
    useEffect(() => {
        const evtSource = new EventSource('/emergency/stream');
        evtSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === 'EMERGENCY_ALERT') {
                    new Audio('/console/alert.mp3').play().catch(() => {});
                    setAlerts(prev => [data, ...prev]);
                }
            } catch (err) {}
        };
        evtSource.onerror = () => evtSource.close();
        return () => evtSource.close();
    }, []);

    const resolveAlert = async (alertId) => {
        try {
            await hubClient.post(`/emergency/${alertId}/resolve`);
            setAlerts(prev => prev.filter(a => a.id !== alertId));
        } catch (e) {
            alert('Failed to mark resolved');
        }
    };

    const saveKioskName = async (kioskId) => {
        if (editingKiosk !== kioskId || editName.trim() === '') {
            setEditingKiosk(null);
            return;
        }
        try {
            await hubClient.put(`/network/kiosk/${kioskId}/name`, { kiosk_name: editName.trim() });
            setKiosks(prev => prev.map(k => k.kiosk_id === kioskId ? { ...k, kiosk_name: editName.trim() } : k));
            setEditingKiosk(null);
            setEditName('');
        } catch (e) {
            alert('Failed to update name');
        }
    };

    if (loading) return <div className="p-8 text-muted">Loading...</div>;

    return (
        <div className="space-y-6">
            <h1 className="page-title">Emergency Calls</h1>

            {/* Active Emergency Alerts */}
            <div className="card">
                <h3 className="section-title">Active Emergency Alerts ({alerts.length})</h3>
                {alerts.length === 0 ? (
                    <p className="text-muted">No active alerts.</p>
                ) : (
                    <div className="space-y-4">
                        {alerts.map((a) => (
                            <div
                                key={a.id}
                                className="p-4 rounded border"
                                style={{ borderColor: 'var(--danger, #b71c1c)', backgroundColor: '#fff5f5' }}
                            >
                                <div className="flex justify-between items-start gap-4">
                                    <div>
                                        <div className="font-semibold text-lg" style={{ color: '#b71c1c' }}>
                                            {a.kiosk_name || a.kiosk_location || a.kiosk_id}
                                        </div>
                                        <div className="text-sm text-muted mt-1">
                                            {new Date(a.timestamp).toLocaleString()}
                                        </div>
                                        {a.transcript && (
                                            <p className="mt-2">{a.transcript}</p>
                                        )}
                                    </div>
                                    <button
                                        className="btn btn-sm"
                                        onClick={() => resolveAlert(a.id)}
                                    >
                                        Mark Resolved
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Connected Kiosks with editable name */}
            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="section-title" style={{ border: 'none', margin: 0, padding: 0 }}>
                        Connected Kiosks ({kiosks.length})
                    </h3>
                    <button className="btn btn-sm" onClick={load}>
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
                <div style={{ overflow: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Kiosk ID</th>
                                <th>Kiosk Name</th>
                                <th>IP Address</th>
                                <th>Last Seen</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {kiosks.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="empty-state">No kiosks connected yet.</td>
                                </tr>
                            ) : (
                                kiosks.map((k) => (
                                    <tr key={k.kiosk_id}>
                                        <td className="font-mono text-sm">{k.kiosk_id}</td>
                                        <td>
                                            {editingKiosk === k.kiosk_id ? (
                                                <input
                                                    className="input"
                                                    style={{ width: '100%', minWidth: 120 }}
                                                    value={editName}
                                                    onChange={(e) => setEditName(e.target.value)}
                                                    onBlur={() => saveKioskName(k.kiosk_id)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') saveKioskName(k.kiosk_id);
                                                        if (e.key === 'Escape') { setEditingKiosk(null); setEditName(''); }
                                                    }}
                                                    autoFocus
                                                />
                                            ) : (
                                                <span
                                                    className="cursor-pointer hover:underline"
                                                    onClick={() => {
                                                        setEditingKiosk(k.kiosk_id);
                                                        setEditName(k.kiosk_name || k.kiosk_id);
                                                    }}
                                                    title="Click to edit"
                                                >
                                                    {k.kiosk_name || k.kiosk_id}
                                                </span>
                                            )}
                                        </td>
                                        <td className="font-mono text-sm">{k.ip || '—'}</td>
                                        <td className="text-sm text-muted">
                                            {k.last_seen ? new Date(k.last_seen + 'Z').toLocaleTimeString() : '—'}
                                        </td>
                                        <td>
                                            <span className={`status-dot ${k.status === 'online' ? 'online' : 'offline'}`}></span>
                                            <span className="text-sm ml-1">{k.status || 'online'}</span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default EmergencyCalls;
