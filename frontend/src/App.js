import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Shared/Sidebar';
import DashboardView from './components/Dashboard/DashboardView';
import UploadView from './components/Upload/UploadView';
import DataCleansingView from './components/DataCleansing/DataCleansingView';
import RiskScoringView from './components/RiskScoring/RiskScoringView';
import AuditLogView from './components/AuditLog/AuditLogView';
import ReportsView from './components/Reports/ReportsView';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import TwoFAModal from './components/TwoFAModal';
import ChangePasswordModal from './components/ChangePasswordModal';
import { useDashboardData } from './hooks/useDashboardData';
import { NAV_ITEMS } from './config/constants';
import { useAuth } from './contexts/AuthContext';
import { LogOut, ShieldCheck, ShieldOff, ChevronDown, Lock } from 'lucide-react';

// Dashboard component (protected)
function SecurePathDashboard() {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const { stats, transactions, loading, refresh } = useDashboardData();
    const { user, logout } = useAuth();

    const renderContent = () => {
        switch (activeTab) {
            case 'dashboard':
                return <DashboardView stats={stats} transactions={transactions} loading={loading} onRefresh={refresh} />;
            case 'upload':
                return <UploadView onSuccess={refresh} />;
            case 'cleansing':
                return <DataCleansingView onSuccess={refresh} />;
            case 'risk-scoring':
                return <RiskScoringView onComplete={refresh} />;
            case 'audit-log':
                return <AuditLogView />;
            case 'reports':
                return <ReportsView />;
            default:
                return <DashboardView stats={stats} transactions={transactions} loading={loading} onRefresh={refresh} />;
        }
    };

    const [showDropdown, setShowDropdown] = useState(false);
    const [show2FAModal, setShow2FAModal] = useState(false);
    const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
    const [twoFAEnabled, setTwoFAEnabled] = useState(null); // null = unknown
    const dropdownRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handler = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const currentNav = NAV_ITEMS.find(i => i.id === activeTab);
    const userInitials = user?.email ? user.email.substring(0, 2).toUpperCase() : 'AD';

    return (
        <ErrorBoundary>
            <div className="flex min-h-screen bg-cyber-dark text-cyber-text-primary selection:bg-cyber-primary selection:text-black">
                <Sidebar
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    sidebarOpen={sidebarOpen}
                    setSidebarOpen={setSidebarOpen}
                />

                <main
                    className={`
                        flex-1 transition-all duration-300 ease-in-out
                        ${sidebarOpen ? 'ml-80' : 'ml-28'} 
                        mr-4 my-4
                        h-[calc(100vh-2rem)] overflow-y-auto custom-scrollbar rounded-xl
                    `}
                >
                    <header className="glass-panel mb-6 p-6 sticky top-4 z-40 flex items-center justify-between">
                        <div>
                            <h2 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
                                {currentNav?.label || 'Dashboard'}
                                <span className="text-sm font-normal text-cyber-text-muted px-3 py-1 rounded-full border border-white/10 bg-black/20">
                                    v2.0.0
                                </span>
                            </h2>
                            <p className="text-cyber-text-secondary mt-1">Real-time fraud detection system</p>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-cyber-success/10 border border-cyber-success/20">
                                <div className="w-2 h-2 bg-cyber-success rounded-full animate-pulse shadow-[0_0_10px_#00FF94]"></div>
                                <span className="text-sm font-bold text-cyber-success tracking-wide">SYSTEM ONLINE</span>
                            </div>
                            {/* Profile dropdown */}
                            <div className="relative" ref={dropdownRef}>
                                <button
                                    onClick={() => setShowDropdown(v => !v)}
                                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                                >
                                    <div className="text-right hidden sm:block">
                                        <p className="text-sm text-white font-medium">{user?.email || 'User'}</p>
                                        <p className="text-xs text-cyber-text-secondary">Logged in</p>
                                    </div>
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-primary to-cyber-secondary p-[2px]">
                                        <div className="w-full h-full rounded-full bg-black flex items-center justify-center text-white font-bold text-sm">
                                            {userInitials}
                                        </div>
                                    </div>
                                    <ChevronDown size={16} className={`text-gray-400 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
                                </button>

                                {showDropdown && (
                                    <div className="absolute right-0 top-14 w-64 bg-gray-900 border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden">
                                        {/* User info */}
                                        <div className="px-4 py-3 border-b border-white/10">
                                            <p className="text-white text-sm font-medium truncate">{user?.email}</p>
                                            <p className="text-gray-400 text-xs mt-0.5">Fraud Detection Analyst</p>
                                        </div>

                                        {/* 2FA option */}
                                        <button
                                            onClick={() => { setShowDropdown(false); setShow2FAModal(true); }}
                                            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-left"
                                        >
                                            {twoFAEnabled === false ? (
                                                <ShieldOff size={18} className="text-gray-400" />
                                            ) : (
                                                <ShieldCheck size={18} className="text-green-400" />
                                            )}
                                            <div>
                                                <p className="text-sm text-white">Two-Factor Auth</p>
                                                <p className={`text-xs ${twoFAEnabled ? 'text-green-400' : 'text-gray-400'}`}>
                                                    {twoFAEnabled === null ? 'Click to manage' : twoFAEnabled ? 'Enabled' : 'Disabled'}
                                                </p>
                                            </div>
                                        </button>

                                        {/* Change password option */}
                                        <button
                                            onClick={() => { setShowDropdown(false); setShowChangePasswordModal(true); }}
                                            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-left"
                                        >
                                            <Lock size={18} className="text-gray-400" />
                                            <div>
                                                <p className="text-sm text-white">Change Password</p>
                                                <p className="text-xs text-gray-400">Requires current password + 2FA</p>
                                            </div>
                                        </button>

                                        {/* Divider */}
                                        <div className="border-t border-white/10" />

                                        {/* Logout */}
                                        <button
                                            onClick={() => { setShowDropdown(false); logout(); }}
                                            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-red-500/10 transition-colors text-left"
                                        >
                                            <LogOut size={18} className="text-red-400" />
                                            <span className="text-sm text-red-400">Sign Out</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </header>

                    <div className="animate-float">
                        {renderContent()}
                    </div>
                </main>
            </div>

            {show2FAModal && (
                <TwoFAModal
                    onClose={() => setShow2FAModal(false)}
                    onStatusChange={(enabled) => setTwoFAEnabled(enabled)}
                />
            )}
            {showChangePasswordModal && (
                <ChangePasswordModal onClose={() => setShowChangePasswordModal(false)} />
            )}
        </ErrorBoundary>
    );
}

// Main App component with routing
export default function App() {
    return (
        <Router>
            <AuthProvider>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                    <Route
                        path="/dashboard"
                        element={
                            <ProtectedRoute>
                                <SecurePathDashboard />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                </Routes>
            </AuthProvider>
        </Router>
    );
}
