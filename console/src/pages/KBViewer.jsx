import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import hubClient from '../api/hubClient';
import { Plus, Edit, Trash2, Save, X, Upload, FileJson, CheckCircle, AlertCircle, Loader } from 'lucide-react';

function KBViewer() {
    const [articles, setArticles] = useState([]);
    const [filter, setFilter] = useState('all');
    const [search, setSearch] = useState('');

    // New-article modal state
    const [showNewModal, setShowNewModal] = useState(false);
    const [formData, setFormData] = useState({
        title: '', body: '', category: 'General', tags: [], enabled: true, status: 'draft'
    });
    const [saving, setSaving] = useState(false);

    // Upload modal state
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [uploadState, setUploadState] = useState('idle');
    const [dragOver, setDragOver] = useState(false);
    const [parsedArticles, setParsedArticles] = useState(null);
    const [uploadResult, setUploadResult] = useState(null);
    const [uploadError, setUploadError] = useState('');
    const fileInputRef = useRef(null);

    useEffect(() => {
        loadArticles();
    }, []);

    const loadArticles = async () => {
        try {
            const res = await hubClient.get('/kb/snapshot');
            setArticles(res.data.articles || []);
        } catch (e) {
            console.error(e);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm("Delete this article?")) return;
        try {
            await hubClient.delete(`/admin/article/${id}`);
            loadArticles();
        } catch (e) {
            alert("Delete failed");
        }
    };

    const filtered = articles.filter(a => {
        if (filter === 'enabled' && !a.enabled) return false;
        if (filter === 'disabled' && a.enabled) return false;
        if (search) {
            const q = search.toLowerCase();
            return a.title.toLowerCase().includes(q) || a.category.toLowerCase().includes(q);
        }
        return true;
    });

    // ─── New Article Modal ───────────────────────────────────────────────

    const resetNewForm = () => {
        setFormData({ title: '', body: '', category: 'General', tags: [], enabled: true, status: 'draft' });
        setSaving(false);
    };

    const openNewModal = () => {
        resetNewForm();
        setShowNewModal(true);
    };

    const closeNewModal = () => {
        setShowNewModal(false);
        resetNewForm();
    };

    const handleNewSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            await hubClient.post('/admin/article', formData);
            closeNewModal();
            loadArticles();
        } catch (e) {
            alert("Save failed");
        } finally {
            setSaving(false);
        }
    };

    // ─── Upload Modal Logic ──────────────────────────────────────────────

    const resetUpload = () => {
        setUploadState('idle');
        setParsedArticles(null);
        setUploadResult(null);
        setUploadError('');
        setDragOver(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const openUploadModal = () => {
        resetUpload();
        setShowUploadModal(true);
    };

    const closeUploadModal = () => {
        setShowUploadModal(false);
        resetUpload();
    };

    const processFile = (file) => {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.json')) {
            setUploadError('Only .json files are accepted.');
            setUploadState('error');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            setUploadError('File too large (max 10 MB).');
            setUploadState('error');
            return;
        }
        setUploadState('parsing');
        setUploadError('');

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const parsed = JSON.parse(e.target.result);
                let arts;
                if (Array.isArray(parsed)) {
                    arts = parsed;
                } else if (parsed.articles && Array.isArray(parsed.articles)) {
                    arts = parsed.articles;
                } else {
                    setUploadError('JSON must be an array of articles or an object with an "articles" key.');
                    setUploadState('error');
                    return;
                }
                if (arts.length === 0) {
                    setUploadError('The JSON file contains no articles.');
                    setUploadState('error');
                    return;
                }
                const invalid = arts.filter(a => !a.title || !a.body);
                if (invalid.length > 0) {
                    setUploadError(`${invalid.length} article(s) are missing a title or body.`);
                    setUploadState('error');
                    return;
                }
                setParsedArticles(arts);
                setUploadState('idle');
            } catch (err) {
                setUploadError(`Invalid JSON: ${err.message}`);
                setUploadState('error');
            }
        };
        reader.onerror = () => {
            setUploadError('Failed to read file.');
            setUploadState('error');
        };
        reader.readAsText(file);
    };

    const handleFilePick = (e) => {
        const file = e.target.files?.[0];
        if (file) processFile(file);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file) processFile(file);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
    };

    const handleImport = async () => {
        if (!parsedArticles || parsedArticles.length === 0) return;
        setUploadState('uploading');
        setUploadError('');
        try {
            const res = await hubClient.post('/admin/import', { articles: parsedArticles }, { timeout: 60000 });
            setUploadResult(res.data);
            setUploadState('success');
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || 'Upload failed.';
            setUploadError(typeof detail === 'string' ? detail : JSON.stringify(detail));
            setUploadState('error');
        }
    };

    // ─── Render ──────────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="page-title">Knowledge Base</h1>
                <div className="flex gap-3">
                    <button onClick={openUploadModal} className="btn">
                        <Upload size={16} /> Upload JSON
                    </button>
                    <button onClick={openNewModal} className="btn btn-primary">
                        <Plus size={16} /> New Article
                    </button>
                </div>
            </div>

            <div className="flex gap-4 items-center">
                <input
                    type="text"
                    placeholder="Search articles..."
                    className="input"
                    style={{ maxWidth: '20rem' }}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
                <select value={filter} onChange={(e) => setFilter(e.target.value)} className="input" style={{ maxWidth: '12rem' }}>
                    <option value="all">All Status</option>
                    <option value="enabled">Enabled</option>
                    <option value="disabled">Disabled</option>
                </select>
                <span className="text-sm text-muted">{filtered.length} articles</span>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table>
                    <thead>
                        <tr>
                            <th>Question</th>
                            <th>Category</th>
                            <th>Status</th>
                            <th>Last Updated</th>
                            <th style={{ width: '5rem' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(a => (
                            <tr key={a.id}>
                                <td style={{ fontWeight: 500 }}>{a.title}</td>
                                <td className="text-muted">{a.category}</td>
                                <td>
                                    <span className={`badge ${a.enabled ? 'badge-success' : 'badge-warning'}`}>
                                        {a.enabled ? 'ENABLED' : 'DISABLED'}
                                    </span>
                                </td>
                                <td className="text-muted text-sm">{new Date(a.updated_at).toLocaleDateString()}</td>
                                <td>
                                    <div className="flex gap-1">
                                        <Link to={`/faq/${a.id}/edit`} className="btn btn-icon" title="Edit">
                                            <Edit size={15} style={{ color: 'var(--primary)' }} />
                                        </Link>
                                        <button onClick={() => handleDelete(a.id)} className="btn btn-icon" title="Delete">
                                            <Trash2 size={15} style={{ color: 'var(--danger)' }} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {filtered.length === 0 && (
                            <tr>
                                <td colSpan="5" className="empty-state">No articles found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* ─── New Article Modal ─── */}
            {showNewModal && (
                <div className="modal-overlay" onClick={closeNewModal}>
                    <div className="modal-content" style={{ maxWidth: '560px' }} onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2 className="modal-title">New Article</h2>
                            <button className="btn-icon" onClick={closeNewModal}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <form onSubmit={handleNewSubmit}>
                                <div className="form-group">
                                    <label>Question / Title</label>
                                    <input
                                        required
                                        className="input"
                                        placeholder="e.g. Where can I get food?"
                                        value={formData.title}
                                        onChange={e => setFormData({ ...formData, title: e.target.value })}
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Answer / Body</label>
                                    <textarea
                                        required
                                        className="textarea"
                                        placeholder="Provide a clear, helpful answer..."
                                        value={formData.body}
                                        onChange={e => setFormData({ ...formData, body: e.target.value })}
                                    />
                                </div>

                                <div className="grid-2" style={{ marginBottom: '1rem' }}>
                                    <div>
                                        <label>Category</label>
                                        <input
                                            className="input"
                                            placeholder="e.g. Food, Medical, Safety"
                                            value={formData.category}
                                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                                        />
                                    </div>
                                    <div>
                                        <label>Tags (comma sep)</label>
                                        <input
                                            className="input"
                                            placeholder="e.g. meals, schedule"
                                            value={formData.tags.join(', ')}
                                            onChange={e => setFormData({ ...formData, tags: e.target.value.split(',').map(s => s.trim()) })}
                                        />
                                    </div>
                                </div>

                                <div className="checkbox-row" style={{ marginBottom: '1.5rem' }}>
                                    <input
                                        type="checkbox"
                                        checked={formData.enabled}
                                        onChange={e => setFormData({ ...formData, enabled: e.target.checked })}
                                        id="enabled"
                                    />
                                    <label htmlFor="enabled">Enabled</label>
                                </div>

                                <div className="flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                    <button type="button" onClick={closeNewModal} className="btn">Cancel</button>
                                    <button type="submit" className="btn btn-primary" disabled={saving}>
                                        <Save size={16} />
                                        {saving ? 'Saving...' : 'Save & Publish'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* ─── Upload JSON Modal ─── */}
            {showUploadModal && (
                <div className="modal-overlay" onClick={closeUploadModal}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <FileJson size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Import Articles from JSON</h2>
                            </div>
                            <button className="btn-icon" onClick={closeUploadModal}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            {uploadState === 'success' && uploadResult && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon success">
                                        <CheckCircle size={48} />
                                    </div>
                                    <h3>Import Complete</h3>
                                    <p className="text-muted text-sm">
                                        {uploadResult.imported} of {uploadResult.total_in_payload} articles imported successfully.
                                        {uploadResult.skipped > 0 && ` ${uploadResult.skipped} skipped.`}
                                    </p>
                                    {uploadResult.errors && uploadResult.errors.length > 0 && (
                                        <div className="upload-errors">
                                            {uploadResult.errors.map((err, i) => (
                                                <div key={i} className="upload-error-line">
                                                    <AlertCircle size={14} />
                                                    <span>{err}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    <div className="flex gap-3 mt-4" style={{ justifyContent: 'center' }}>
                                        <button onClick={() => { closeUploadModal(); loadArticles(); }} className="btn btn-primary">
                                            Done
                                        </button>
                                        <button onClick={resetUpload} className="btn">
                                            Import More
                                        </button>
                                    </div>
                                </div>
                            )}

                            {uploadState === 'error' && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon error">
                                        <AlertCircle size={48} />
                                    </div>
                                    <h3>Something went wrong</h3>
                                    <p className="text-muted text-sm">{uploadError}</p>
                                    <button onClick={resetUpload} className="btn mt-4">
                                        Try Again
                                    </button>
                                </div>
                            )}

                            {uploadState === 'uploading' && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon uploading">
                                        <Loader size={48} className="spin" />
                                    </div>
                                    <h3>Importing {parsedArticles?.length} articles...</h3>
                                    <p className="text-muted text-sm">Embedding and saving to the knowledge base. This may take a moment.</p>
                                </div>
                            )}

                            {uploadState === 'parsing' && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon uploading">
                                        <Loader size={48} className="spin" />
                                    </div>
                                    <h3>Reading file...</h3>
                                </div>
                            )}

                            {uploadState === 'idle' && !parsedArticles && (
                                <>
                                    <div
                                        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
                                        onDrop={handleDrop}
                                        onDragOver={handleDragOver}
                                        onDragLeave={handleDragLeave}
                                        onClick={() => fileInputRef.current?.click()}
                                    >
                                        <Upload size={32} style={{ color: dragOver ? 'var(--primary)' : 'var(--text-muted)' }} />
                                        <p className="drop-zone-title">
                                            {dragOver ? 'Drop your file here' : 'Drag & drop a JSON file here'}
                                        </p>
                                        <p className="drop-zone-hint">or click to browse</p>
                                        <input
                                            ref={fileInputRef}
                                            type="file"
                                            accept=".json,application/json"
                                            onChange={handleFilePick}
                                            style={{ display: 'none' }}
                                        />
                                    </div>

                                    <div className="upload-format-hint">
                                        <p className="font-semibold text-sm" style={{ marginBottom: '0.25rem' }}>Expected format:</p>
                                        <pre className="format-preview">{`[
  {
    "title": "Where do I get food?",
    "body": "Meals are served at...",
    "category": "Food",
    "tags": ["meals", "food"],
    "status": "published",
    "enabled": true
  },
  ...
]`}</pre>
                                    </div>
                                </>
                            )}

                            {uploadState === 'idle' && parsedArticles && (
                                <div className="upload-preview">
                                    <div className="upload-preview-header">
                                        <div className="flex items-center gap-2">
                                            <CheckCircle size={18} style={{ color: 'var(--success)' }} />
                                            <span className="font-semibold">{parsedArticles.length} articles ready to import</span>
                                        </div>
                                        <button onClick={resetUpload} className="btn btn-sm">
                                            Change File
                                        </button>
                                    </div>

                                    <div className="upload-preview-list">
                                        {parsedArticles.slice(0, 8).map((art, i) => (
                                            <div key={i} className="upload-preview-item">
                                                <span className="upload-preview-num">{i + 1}</span>
                                                <div>
                                                    <div className="font-medium text-sm">{art.title}</div>
                                                    <div className="text-xs text-muted">{art.category || 'General'} · {(art.tags || []).length} tags</div>
                                                </div>
                                            </div>
                                        ))}
                                        {parsedArticles.length > 8 && (
                                            <div className="text-muted text-xs text-center" style={{ padding: '0.5rem' }}>
                                                ... and {parsedArticles.length - 8} more
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex gap-3 mt-4" style={{ justifyContent: 'flex-end' }}>
                                        <button onClick={closeUploadModal} className="btn">Cancel</button>
                                        <button onClick={handleImport} className="btn btn-primary">
                                            <Upload size={16} />
                                            Import {parsedArticles.length} Articles
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default KBViewer;
