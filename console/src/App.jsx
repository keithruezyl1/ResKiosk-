import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Book, FileText, Settings, Wifi, Terminal, Phone, MessageSquare, Moon, Sun } from 'lucide-react';
import hubClient from './api/hubClient';
import logoSvg from './assets/reskiosk-logo.svg';

// Pages
import Dashboard from './pages/Dashboard';
import KBViewer from './pages/KBViewer';
import FAQManager from './pages/FAQManager';
import ShelterConfig from './pages/ShelterConfig';
import NetworkSetup from './pages/NetworkSetup';
import LogsViewer from './pages/LogsViewer';
import EmergencyCalls from './pages/EmergencyCalls';
import HubMessages from './pages/HubMessages';

function App() {
    const [emergencyMode, setEmergencyMode] = useState(false);
    const [activeAlertCount, setActiveAlertCount] = useState(0);
    const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
    const location = useLocation();

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
        localStorage.setItem('theme', darkMode ? 'dark' : 'light');
    }, [darkMode]);

    useEffect(() => {
        const checkStatus = async () => {
            try {
                await hubClient.get('/admin/ping');
                const snap = await hubClient.get('/kb/snapshot');
                if (snap.data.structured_config && snap.data.structured_config.emergency_mode === true) {
                    setEmergencyMode(true);
                } else {
                    setEmergencyMode(false);
                }
            } catch (e) {
                console.error("Status check failed", e);
            }
        };
        checkStatus();
        const interval = setInterval(checkStatus, 10000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const fetchAlerts = async () => {
            try {
                const res = await hubClient.get('/emergency/active');
                setActiveAlertCount((res.data.alerts || []).length);
            } catch (e) { }
        };
        fetchAlerts();
        const interval = setInterval(fetchAlerts, 5000);
        return () => clearInterval(interval);
    }, []);

    const NavItem = ({ to, icon: Icon, label, highlight }) => {
        const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
        const isExactRoot = to === '/' && location.pathname === '/';
        const active = isActive || isExactRoot;
        return (
            <Link to={to}
                className={`nav-item ${active ? 'active' : ''} ${highlight ? 'highlight' : ''}`}
            >
                <Icon size={18} />
                <span>{label}</span>
            </Link>
        );
    };

    return (
        <div className="app-shell">
            {emergencyMode && (
                <div className="banner-emergency">
                    ⚠ EMERGENCY MODE ACTIVE
                </div>
            )}
            {activeAlertCount > 0 && (
                <div className="banner-emergency" style={{ backgroundColor: '#b71c1c' }}>
                    <span className="pulse-dot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: '#fff', marginRight: 8, animation: 'pulse 1s ease-in-out infinite' }}></span>
                    <strong>{activeAlertCount}</strong> active emergency alert(s) —
                    <Link to="/emergency" style={{ color: '#fff', textDecoration: 'underline', marginLeft: 6 }}>View now</Link>
                </div>
            )}

            <div className="app-layout">
                {/* Sidebar */}
                <aside className="sidebar">
                    <div className="sidebar-header">
                        <div className="sidebar-brand">
                            <img src={logoSvg} alt="ResKiosk" />
                            <h1>ResKiosk Hub</h1>
                        </div>
                    </div>

                    <nav className="sidebar-nav">
                        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" />
                        <NavItem to="/kb" icon={Book} label="KB Viewer" />

                        <NavItem to="/config" icon={Settings} label="Shelter Config" />
                        <NavItem to="/network" icon={Wifi} label="Network Setup" />
                        <NavItem to="/emergency" icon={Phone} label="Emergency Calls" />
                        <NavItem to="/messages" icon={MessageSquare} label="Hub Messages" />
                        <NavItem to="/logs" icon={Terminal} label="Logs" highlight={false} />
                    </nav>

                    <div style={{ padding: '0.75rem' }}>
                        <button className="theme-toggle" onClick={() => setDarkMode(d => !d)}>
                            {darkMode ? <Sun size={16} /> : <Moon size={16} />}
                            <span>{darkMode ? 'Light Mode' : 'Night Mode'}</span>
                        </button>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Dashboard setEmergencyMode={setEmergencyMode} />} />
                        <Route path="/kb" element={<KBViewer />} />

                        <Route path="/faq/:id/edit" element={<FAQManager isNew={false} />} />
                        <Route path="/config" element={<ShelterConfig />} />
                        <Route path="/network" element={<NetworkSetup />} />
                        <Route path="/emergency" element={<EmergencyCalls />} />
                        <Route path="/messages" element={<HubMessages />} />
                        <Route path="/logs" element={<LogsViewer />} />
                    </Routes>
                </main>
            </div>
        </div>
    );
}

export default App;
