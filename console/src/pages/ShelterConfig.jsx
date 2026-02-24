import React, { useState, useEffect } from 'react';
import hubClient from '../api/hubClient';
import { Save } from 'lucide-react';

function ShelterConfig() {
    const [config, setConfig] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        try {
            const res = await hubClient.get('/kb/snapshot');
            setConfig(res.data.structured_config || {});
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (key, newVal) => {
        try {
            await hubClient.put(`/admin/config/${key}`, { value: newVal });
            setConfig(prev => ({ ...prev, [key]: newVal }));
            alert(`Updated ${key}`);
        } catch (e) {
            alert("Update failed");
        }
    };

    const configKeys = () => Object.keys(config).filter(k => k !== 'inventory');

    const publishAll = async () => {
        try {
            await hubClient.post('/admin/publish');
            alert('Published!');
        } catch (e) {
            alert('Publish failed');
        }
    };

    if (loading) return <div className="p-8 text-muted">Loading configuration...</div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="page-title">Shelter Configuration</h1>
                <p className="text-sm text-muted mt-1">Edit shelter settings.</p>
            </div>

            {/* Config keys (raw JSON) */}
            <div className="card">
                <h3 className="section-title">Settings</h3>
                {configKeys().length === 0 ? (
                    <div className="empty-state">No configuration keys.</div>
                ) : (
                    <div className="space-y-2">
                        {configKeys().map((key) => (
                            <div key={key} className="config-field">
                                <label>{key.replace(/_/g, ' ')}</label>
                                <div className="flex gap-2 mt-1">
                                    <textarea
                                        className="textarea"
                                        style={{ minHeight: '3.5rem' }}
                                        defaultValue={JSON.stringify(config[key], null, 2)}
                                        onBlur={(e) => {
                                            try {
                                                const val = JSON.parse(e.target.value);
                                                handleUpdate(key, val);
                                            } catch (err) {}
                                        }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex justify-end">
                <button onClick={publishAll} className="btn btn-primary">
                    <Save size={16} />
                    Publish All Changes
                </button>
            </div>
        </div>
    );
}

export default ShelterConfig;

