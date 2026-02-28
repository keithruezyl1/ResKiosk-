import React, { useState, useEffect } from 'react';
import hubClient from '../api/hubClient';
import { Send, Trash2, Eye, X, Radio, ChevronDown } from 'lucide-react';

const PRIORITY_COLORS = {
    normal: { bg: 'var(--bg-secondary)', color: 'var(--text-muted)', label: 'Normal' },
    urgent: { bg: '#ffa726', color: '#fff', label: 'Urgent' },
    emergency: { bg: 'var(--danger)', color: '#fff', label: 'Emergency' },
};

const STATUS_COLORS = {
    pending: { bg: 'var(--warning)', color: '#fff' },
    read: { bg: 'var(--primary)', color: '#fff' },
    published: { bg: 'var(--success)', color: '#fff' },
    rejected: { bg: 'var(--danger)', color: '#fff' },
};

function HubMessages() {
    const [messages, setMessages] = useState([]);
    const [categories, setCategories] = useState([]);
    const [hubs, setHubs] = useState([]);
    const [filterStatus, setFilterStatus] = useState('all');
    const [showCompose, setShowCompose] = useState(false);
    const [viewMsg, setViewMsg] = useState(null);
    const [loading, setLoading] = useState(true);

    // Compose form
    const [form, setForm] = useState({
        subject: '', content: '', category_id: '', target_hub_id: '', priority: 'normal'
    });
    const [sending, setSending] = useState(false);

    useEffect(() => {
        loadAll();
    }, []);

    const loadAll = async () => {
        try {
            const [msgRes, catRes, hubRes] = await Promise.all([
                hubClient.get('/messages'),
                hubClient.get('/messages/categories'),
                hubClient.get('/messages/hubs'),
            ]);
            setMessages(msgRes.data.messages || []);
            setCategories(catRes.data.categories || []);
            setHubs(hubRes.data.hubs || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        setSending(true);
        try {
            const payload = {
                subject: form.subject,
                content: form.content,
                priority: form.priority,
                category_id: form.category_id ? parseInt(form.category_id) : null,
                target_hub_id: form.target_hub_id ? parseInt(form.target_hub_id) : null,
            };
            await hubClient.post('/messages', payload);
            setShowCompose(false);
            setForm({ subject: '', content: '', category_id: '', target_hub_id: '', priority: 'normal' });
            loadAll();
        } catch (e) {
            alert('Failed to send message.');
        } finally {
            setSending(false);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this message?')) return;
        try {
            await hubClient.delete(`/messages/${id}`);
            if (viewMsg && viewMsg.id === id) setViewMsg(null);
            loadAll();
        } catch (e) {
            alert('Delete failed.');
        }
    };

    const handleStatusChange = async (id, status) => {
        try {
            const res = await hubClient.put(`/messages/${id}`, { status });
            if (viewMsg && viewMsg.id === id) setViewMsg(res.data);
            loadAll();
        } catch (e) {
            alert('Status update failed.');
        }
    };

    const filtered = messages.filter(m => {
        if (filterStatus !== 'all' && m.status !== filterStatus) return false;
        return true;
    });

    const fmtTime = (ts) => {
        if (!ts) return '—';
        return new Date(ts * 1000).toLocaleString();
    };

    if (loading) {
        return <div className="space-y-6"><h1 className="page-title">Hub Messages</h1><p className="text-muted">Loading...</p></div>;
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <h1 className="page-title">Hub Messages</h1>
                <button className="btn btn-primary" onClick={() => setShowCompose(true)}>
                    <Send size={16} /> Compose
                </button>
            </div>

            {/* Filters */}
            <div className="flex gap-4 items-center">
                <select
                    value={filterStatus}
                    onChange={e => setFilterStatus(e.target.value)}
                    className="input"
                    style={{ maxWidth: '12rem' }}
                >
                    <option value="all">All Status</option>
                    <option value="pending">Pending</option>
                    <option value="read">Read</option>
                    <option value="published">Published</option>
                    <option value="rejected">Rejected</option>
                </select>
                <span className="text-sm text-muted">{filtered.length} message(s)</span>
            </div>

            {/* Messages Table */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table>
                    <thead>
                        <tr>
                            <th>Subject</th>
                            <th>Category</th>
                            <th>Target</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Sent</th>
                            <th style={{ width: '6rem' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(m => {
                            const pri = PRIORITY_COLORS[m.priority] || PRIORITY_COLORS.normal;
                            const st = STATUS_COLORS[m.status] || STATUS_COLORS.pending;
                            return (
                                <tr key={m.id} style={{ cursor: 'pointer' }} onClick={() => setViewMsg(m)}>
                                    <td style={{ fontWeight: 500 }}>{m.subject || '(no subject)'}</td>
                                    <td className="text-muted">{m.category_name || '—'}</td>
                                    <td className="text-muted">{m.target_hub_name || 'Broadcast'}</td>
                                    <td>
                                        <span className="badge" style={{ background: pri.bg, color: pri.color, fontSize: '0.7rem' }}>
                                            {pri.label}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="badge" style={{ background: st.bg, color: st.color, fontSize: '0.7rem', textTransform: 'uppercase' }}>
                                            {m.status}
                                        </span>
                                    </td>
                                    <td className="text-muted text-sm">{fmtTime(m.sent_at)}</td>
                                    <td>
                                        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                            <button onClick={() => setViewMsg(m)} className="btn btn-icon" title="View">
                                                <Eye size={15} style={{ color: 'var(--primary)' }} />
                                            </button>
                                            <button onClick={() => handleDelete(m.id)} className="btn btn-icon" title="Delete">
                                                <Trash2 size={15} style={{ color: 'var(--danger)' }} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                        {filtered.length === 0 && (
                            <tr>
                                <td colSpan="7" className="empty-state">No messages found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* ─── Compose Modal ─── */}
            {showCompose && (
                <div className="modal-overlay" onClick={() => setShowCompose(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '34rem' }}>
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <Send size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Compose Message</h2>
                            </div>
                            <button className="btn-icon" onClick={() => setShowCompose(false)}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <form onSubmit={handleSend}>
                                <div className="form-group">
                                    <label>Subject</label>
                                    <input
                                        required
                                        className="input"
                                        placeholder="Message subject..."
                                        value={form.subject}
                                        onChange={e => setForm({ ...form, subject: e.target.value })}
                                    />
                                </div>

                                <div className="grid-2" style={{ marginBottom: '1rem' }}>
                                    <div>
                                        <label>Category</label>
                                        <select
                                            className="input"
                                            value={form.category_id}
                                            onChange={e => setForm({ ...form, category_id: e.target.value })}
                                        >
                                            <option value="">— Select —</option>
                                            {categories.map(c => (
                                                <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label>Target Hub</label>
                                        <select
                                            className="input"
                                            value={form.target_hub_id}
                                            onChange={e => setForm({ ...form, target_hub_id: e.target.value })}
                                        >
                                            <option value="">Broadcast (all hubs)</option>
                                            {hubs.map(h => (
                                                <option key={h.hub_id} value={h.hub_id}>{h.hub_name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Priority</label>
                                    <div className="flex gap-3">
                                        {['normal', 'urgent', 'emergency'].map(p => {
                                            const pri = PRIORITY_COLORS[p];
                                            const selected = form.priority === p;
                                            return (
                                                <button
                                                    type="button"
                                                    key={p}
                                                    className="btn btn-sm"
                                                    style={{
                                                        background: selected ? pri.bg : 'transparent',
                                                        color: selected ? pri.color : 'var(--text-muted)',
                                                        border: `1px solid ${selected ? pri.bg : 'var(--border)'}`,
                                                        fontWeight: selected ? 600 : 400,
                                                    }}
                                                    onClick={() => setForm({ ...form, priority: p })}
                                                >
                                                    {pri.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Content</label>
                                    <textarea
                                        required
                                        className="textarea"
                                        placeholder="Write your message..."
                                        rows={5}
                                        value={form.content}
                                        onChange={e => setForm({ ...form, content: e.target.value })}
                                    />
                                </div>

                                <div className="flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                    <button type="button" onClick={() => setShowCompose(false)} className="btn">Cancel</button>
                                    <button type="submit" className="btn btn-primary" disabled={sending}>
                                        <Send size={16} />
                                        {sending ? 'Sending...' : 'Send Message'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* ─── View Message Modal ─── */}
            {viewMsg && (
                <div className="modal-overlay" onClick={() => setViewMsg(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '36rem' }}>
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <Radio size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Message Detail</h2>
                            </div>
                            <button className="btn-icon" onClick={() => setViewMsg(null)}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div style={{ marginBottom: '1.25rem' }}>
                                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{viewMsg.subject || '(no subject)'}</h3>
                                <div className="flex gap-2 items-center" style={{ marginTop: '0.5rem' }}>
                                    {(() => {
                                        const pri = PRIORITY_COLORS[viewMsg.priority] || PRIORITY_COLORS.normal;
                                        const st = STATUS_COLORS[viewMsg.status] || STATUS_COLORS.pending;
                                        return (
                                            <>
                                                <span className="badge" style={{ background: pri.bg, color: pri.color, fontSize: '0.7rem' }}>{pri.label}</span>
                                                <span className="badge" style={{ background: st.bg, color: st.color, fontSize: '0.7rem', textTransform: 'uppercase' }}>{viewMsg.status}</span>
                                            </>
                                        );
                                    })()}
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                                <div><strong>From:</strong> {viewMsg.source_hub_name || '—'}</div>
                                <div><strong>To:</strong> {viewMsg.target_hub_name || 'Broadcast'}</div>
                                <div><strong>Category:</strong> {viewMsg.category_name || '—'}</div>
                                <div><strong>Via:</strong> {viewMsg.received_via || '—'}</div>
                                <div><strong>Sent:</strong> {fmtTime(viewMsg.sent_at)}</div>
                                <div><strong>Received:</strong> {fmtTime(viewMsg.received_at)}</div>
                            </div>

                            <div style={{ background: 'var(--bg-secondary)', borderRadius: '0.5rem', padding: '1rem', marginBottom: '1.25rem', whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: 1.6 }}>
                                {viewMsg.content || '(no content)'}
                            </div>

                            {/* Status Actions */}
                            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                <label style={{ fontSize: '0.8rem', marginBottom: '0.5rem', display: 'block', color: 'var(--text-muted)' }}>
                                    Change Status
                                </label>
                                <div className="flex gap-2 flex-wrap">
                                    {['pending', 'read', 'published', 'rejected'].map(s => {
                                        const st = STATUS_COLORS[s];
                                        const isCurrent = viewMsg.status === s;
                                        return (
                                            <button
                                                key={s}
                                                className="btn btn-sm"
                                                disabled={isCurrent}
                                                style={{
                                                    background: isCurrent ? st.bg : 'transparent',
                                                    color: isCurrent ? st.color : 'var(--text)',
                                                    border: `1px solid ${isCurrent ? st.bg : 'var(--border)'}`,
                                                    opacity: isCurrent ? 1 : 0.8,
                                                    textTransform: 'capitalize',
                                                }}
                                                onClick={() => handleStatusChange(viewMsg.id, s)}
                                            >
                                                {s}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="flex justify-end gap-3" style={{ marginTop: '1rem' }}>
                                <button className="btn" style={{ color: 'var(--danger)' }} onClick={() => { handleDelete(viewMsg.id); setViewMsg(null); }}>
                                    <Trash2 size={15} /> Delete
                                </button>
                                <button className="btn" onClick={() => setViewMsg(null)}>Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default HubMessages;
