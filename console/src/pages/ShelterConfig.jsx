import React, { useState, useEffect } from 'react';
import hubClient from '../api/hubClient';
import { Save, Plus, Trash2, Info, MapPin, Heart, ClipboardCheck, Bell } from 'lucide-react';

function ShelterConfig() {
    const [subFields, setSubFields] = useState({
        food: {
            breakfast: { time: '', desc: '' },
            lunch: { time: '', desc: '' },
            dinner: { time: '', desc: '' }
        },
        sleeping: [{ location: '', details: '' }],
        medical: { location: '', hours: '', contact: '' },
        registration: [{ step: 'Step 1', procedure: '' }, { step: 'Step 2', procedure: '' }],
        announcements: { headline: '', content: '' }
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        loadConfig();
    }, []);

    const loadConfig = async () => {
        try {
            const res = await hubClient.get('/admin/evac');
            const data = res.data;
            if (data.metadata) {
                try {
                    const parsed = JSON.parse(data.metadata);
                    if (parsed.subFields) {
                        setSubFields(parsed.subFields);
                        setLoading(false);
                        return;
                    }
                } catch (e) { }
            }

            // Fallback: Populate if metadata is empty
            const initial = { ...subFields };
            if (data.food_schedule) initial.food.breakfast.time = data.food_schedule;
            if (data.sleeping_zones) initial.sleeping[0].location = data.sleeping_zones;
            if (data.medical_station) initial.medical.location = data.medical_station;
            if (data.registration_steps) initial.registration[0].procedure = data.registration_steps;
            if (data.announcements) initial.announcements.content = data.announcements;
            setSubFields(initial);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            // Concatenate strings for legacy kiosk columns
            const food_schedule = `Breakfast: ${subFields.food.breakfast.desc} | Lunch: ${subFields.food.lunch.desc} | Dinner: ${subFields.food.dinner.desc}`;
            const sleeping_zones = subFields.sleeping.map(s => `${s.location}: ${s.details}`).join(', ');
            const medical_station = `${subFields.medical.location} (${subFields.medical.hours}) - Contact: ${subFields.medical.contact}`;
            const registration_steps = subFields.registration.map((r, i) => `Step ${i + 1}: ${r.procedure}`).join(', ');
            const announcements = `[${subFields.announcements.headline}] ${subFields.announcements.content}`;

            const payload = {
                food_schedule,
                sleeping_zones,
                medical_station,
                registration_steps,
                announcements,
                metadata: JSON.stringify({ subFields })
            };

            await hubClient.put('/admin/evac', payload);
            await hubClient.post('/admin/publish');
            alert('Shelter configuration updated and published!');
        } catch (e) {
            console.error(e);
            alert('Failed to save configuration.');
        } finally {
            setSaving(false);
        }
    };

    const updateFood = (meal, field, val) => {
        setSubFields(prev => ({
            ...prev,
            food: {
                ...prev.food,
                [meal]: { ...prev.food[meal], [field]: val }
            }
        }));
    };

    const updateMedical = (field, val) => {
        setSubFields(prev => ({
            ...prev,
            medical: { ...prev.medical, [field]: val }
        }));
    };

    const updateAnnouncement = (field, val) => {
        setSubFields(prev => ({
            ...prev,
            announcements: { ...prev.announcements, [field]: val }
        }));
    };

    // Dynamic Row Helpers
    const addSleepingRow = () => {
        setSubFields(prev => ({
            ...prev,
            sleeping: [...prev.sleeping, { location: '', details: '' }]
        }));
    };

    const removeSleepingRow = (index) => {
        if (subFields.sleeping.length <= 1) return;
        setSubFields(prev => ({
            ...prev,
            sleeping: prev.sleeping.filter((_, i) => i !== index)
        }));
    };

    const updateSleepingRow = (index, field, val) => {
        const next = [...subFields.sleeping];
        next[index][field] = val;
        setSubFields(prev => ({ ...prev, sleeping: next }));
    };

    const addRegistrationRow = () => {
        const nextStepNum = subFields.registration.length + 1;
        setSubFields(prev => ({
            ...prev,
            registration: [...prev.registration, { step: `Step ${nextStepNum}`, procedure: '' }]
        }));
    };

    const removeRegistrationRow = (index) => {
        if (subFields.registration.length <= 1) return;
        const next = subFields.registration.filter((_, i) => i !== index).map((r, i) => ({
            ...r,
            step: `Step ${i + 1}`
        }));
        setSubFields(prev => ({ ...prev, registration: next }));
    };

    const updateRegistrationRow = (index, val) => {
        const next = [...subFields.registration];
        next[index].procedure = val;
        setSubFields(prev => ({ ...prev, registration: next }));
    };

    if (loading) return <div className="p-8 text-muted">Loading configuration...</div>;

    return (
        <div className="max-w-5xl space-y-6">
            <div className="flex justify-between items-center mb-2">
                <div>
                    <h1 className="page-title">Shelter Configuration</h1>
                    <p className="text-sm text-muted">Manage operational details and facility schedules.</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn btn-primary px-6 h-10"
                >
                    <Save size={16} />
                    {saving ? 'Saving...' : 'Save & Publish'}
                </button>
            </div>

            {/* Food Schedule Section */}
            <div className="config-section">
                <span className="config-section-title">Food & Nutrition</span>
                <div className="space-y-6 mt-4">
                    {['breakfast', 'lunch', 'dinner'].map((meal) => (
                        <div key={meal} className="form-group mb-0">
                            <label className="text-main font-normal" style={{ fontSize: '0.925rem' }}>
                                {meal.charAt(0).toUpperCase() + meal.slice(1)}
                            </label>
                            <input
                                className="input w-full mt-1"
                                value={subFields.food[meal].desc}
                                onChange={e => updateFood(meal, 'desc', e.target.value)}
                                placeholder={`Enter ${meal} schedule and details...`}
                            />
                        </div>
                    ))}
                </div>
                <p className="form-hint mt-6">Displayed on kiosks under "Food & Water" schedule.</p>
            </div>

            {/* Sleeping Zones Section */}
            <div className="config-section">
                <span className="config-section-title">Sleeping Areas</span>
                <div className="space-y-4">
                    {subFields.sleeping.map((row, idx) => (
                        <div key={idx} className="dynamic-row">
                            <div className="form-group">
                                <label className="font-normal text-muted">Location</label>
                                <input className="input" value={row.location} onChange={e => updateSleepingRow(idx, 'location', e.target.value)} placeholder="e.g. Zone A (Gymnasium)" />
                            </div>
                            <div className="form-group" style={{ flex: 1.5 }}>
                                <label className="font-normal text-muted">Details</label>
                                <input className="input" value={row.details} onChange={e => updateSleepingRow(idx, 'details', e.target.value)} placeholder="e.g. General population, cots provided" />
                            </div>
                            <button className="row-action-btn danger mb-[2px]" onClick={() => removeSleepingRow(idx)} disabled={subFields.sleeping.length === 1}>
                                <Trash2 size={14} />
                            </button>
                        </div>
                    ))}
                </div>
                <button className="add-row-trigger" onClick={addSleepingRow}>
                    <Plus size={16} /> Add Area
                </button>
            </div>

            {/* Medical Services Section */}
            <div className="config-section">
                <span className="config-section-title">Medical & Well-being</span>
                <div className="form-group mb-4">
                    <label className="font-normal text-muted">Station Location</label>
                    <input className="input" value={subFields.medical.location} onChange={e => updateMedical('location', e.target.value)} placeholder="e.g. West Corridor, Room 104" />
                </div>
                <div className="form-grid-2">
                    <div className="form-group">
                        <label className="font-normal text-muted">Operating Hours</label>
                        <input className="input" value={subFields.medical.hours} onChange={e => updateMedical('hours', e.target.value)} placeholder="e.g. 24/7 or 08AM - 10PM" />
                    </div>
                    <div className="form-group">
                        <label className="font-normal text-muted">Contact Info</label>
                        <input className="input" value={subFields.medical.contact} onChange={e => updateMedical('contact', e.target.value)} placeholder="e.g. Nurse Desk / Extension 5" />
                    </div>
                </div>
            </div>

            {/* Registration Procedure Section */}
            <div className="config-section">
                <span className="config-section-title">Intake & Registration</span>
                <div className="space-y-4">
                    {subFields.registration.map((row, idx) => (
                        <div key={idx} className="dynamic-row">
                            <div className="form-group">
                                <label className="font-normal text-muted">{row.step}</label>
                                <input className="input" value={row.procedure} onChange={e => updateRegistrationRow(idx, e.target.value)} placeholder={`Instruction for ${row.step.toLowerCase()}...`} />
                            </div>
                            <button className="row-action-btn danger mb-[2px]" onClick={() => removeRegistrationRow(idx)} disabled={subFields.registration.length <= 1}>
                                <Trash2 size={14} />
                            </button>
                        </div>
                    ))}
                </div>
                <button className="add-row-trigger" onClick={addRegistrationRow}>
                    <Plus size={16} /> Add Step
                </button>
            </div>

            {/* Announcements Section */}
            <div className="config-section">
                <span className="config-section-title">Public Communication</span>
                <div className="form-group mb-4">
                    <label className="font-normal text-muted">Feature Headline</label>
                    <input className="input font-bold" value={subFields.announcements.headline} onChange={e => updateAnnouncement('headline', e.target.value)} placeholder="e.g. SHOWER SCHEDULE UPDATE" />
                </div>
                <div className="form-group">
                    <label className="font-normal text-muted">Announcement Details</label>
                    <textarea className="textarea" style={{ minHeight: '120px' }} value={subFields.announcements.content} onChange={e => updateAnnouncement('content', e.target.value)} placeholder="Type the full message to be displayed on kiosks..." />
                </div>
            </div>
        </div>
    );
}

export default ShelterConfig;
