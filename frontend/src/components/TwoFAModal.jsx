import React, { useState, useEffect, useRef } from 'react';
import authService from '../services/authService';
import { ShieldCheck, ShieldOff, X, Copy, Check, Loader, AlertCircle, CheckCircle, Lock } from 'lucide-react';

/**
 * TwoFAModal
 * Props:
 *   onClose()          — called when the modal is dismissed
 *   onStatusChange()   — called after 2FA is successfully enabled or disabled
 */
export default function TwoFAModal({ onClose, onStatusChange }) {
    const [view, setView] = useState('loading');   // loading | status | setup | disable | backup
    const [is2FAEnabled, setIs2FAEnabled] = useState(false);

    // Setup state
    const [qrCode, setQrCode] = useState('');
    const [manualKey, setManualKey] = useState('');
    const [otp, setOtp] = useState('');
    const [copied, setCopied] = useState(false);
    const [backupCodes, setBackupCodes] = useState([]);

    // Disable state
    const [disablePassword, setDisablePassword] = useState('');
    const [disableOtp, setDisableOtp] = useState('');

    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const otpRef = useRef(null);

    // Load current 2FA status on open
    useEffect(() => {
        (async () => {
            try {
                const status = await authService.get2FAStatus();
                setIs2FAEnabled(status.is_2fa_enabled);
                setView('status');
            } catch {
                setView('status');
            }
        })();
    }, []);

    useEffect(() => {
        if ((view === 'setup' || view === 'disable') && otpRef.current) {
            otpRef.current.focus();
        }
    }, [view]);

    const handleOtpChange = (setter) => (e) =>
        setter(e.target.value.replace(/\D/g, '').slice(0, 6));

    // ── Start setup ───────────────────────────────────────────────────────────
    const startSetup = async () => {
        setError('');
        setLoading(true);
        try {
            const data = await authService.setup2FA();
            setQrCode(data.qr_code);
            setManualKey(data.manual_key);
            setView('setup');
        } catch (err) {
            setError(err.message || 'Failed to start 2FA setup');
        } finally {
            setLoading(false);
        }
    };

    // ── Verify OTP and enable ────────────────────────────────────────────────
    const handleEnable = async (e) => {
        e.preventDefault();
        setError('');
        if (!/^\d{6}$/.test(otp)) { setError('Enter the 6-digit code from your app'); return; }
        setLoading(true);
        try {
            const data = await authService.enable2FA(otp);
            setBackupCodes(data.backup_codes || []);
            setIs2FAEnabled(true);
            setView('backup');
            onStatusChange(true);
        } catch (err) {
            setError(err.message || 'Invalid code');
            setOtp('');
        } finally {
            setLoading(false);
        }
    };

    // ── Disable 2FA ──────────────────────────────────────────────────────────
    const handleDisable = async (e) => {
        e.preventDefault();
        setError('');
        if (!disablePassword) { setError('Password is required'); return; }
        if (!/^\d{6}$/.test(disableOtp)) { setError('Enter your 6-digit authenticator code'); return; }
        setLoading(true);
        try {
            await authService.disable2FA(disablePassword, disableOtp);
            setIs2FAEnabled(false);
            onStatusChange(false);
            onClose();
        } catch (err) {
            setError(err.message || 'Failed to disable 2FA');
            setDisableOtp('');
        } finally {
            setLoading(false);
        }
    };

    const copyKey = () => {
        navigator.clipboard.writeText(manualKey);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-md bg-gray-900 border border-white/10 rounded-2xl shadow-2xl p-6 relative">

                {/* Close button */}
                <button onClick={onClose}
                    className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors">
                    <X size={18} />
                </button>

                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-2">
                        <AlertCircle className="text-red-400 flex-shrink-0" size={16} />
                        <p className="text-red-400 text-sm">{error}</p>
                    </div>
                )}

                {/* ── Loading ── */}
                {view === 'loading' && (
                    <div className="flex justify-center py-10">
                        <Loader className="animate-spin text-blue-400" size={28} />
                    </div>
                )}

                {/* ── Status overview ── */}
                {view === 'status' && (
                    <div className="space-y-5">
                        <div className="flex items-center gap-3">
                            {is2FAEnabled
                                ? <ShieldCheck className="text-green-400" size={24} />
                                : <ShieldOff className="text-gray-400" size={24} />}
                            <div>
                                <h2 className="text-white font-semibold text-lg">Two-Factor Authentication</h2>
                                <p className={`text-sm font-medium ${is2FAEnabled ? 'text-green-400' : 'text-gray-400'}`}>
                                    {is2FAEnabled ? 'Enabled' : 'Disabled'}
                                </p>
                            </div>
                        </div>

                        <p className="text-gray-400 text-sm">
                            {is2FAEnabled
                                ? 'Your account is protected with a second factor. You will be asked for a code from your authenticator app each time you log in.'
                                : 'Add an extra layer of security. After enabling, you will need your phone to log in.'}
                        </p>

                        {is2FAEnabled ? (
                            <button onClick={() => { setError(''); setView('disable'); }}
                                className="w-full py-3 bg-red-600/20 hover:bg-red-600/30 border border-red-500/40 text-red-400 font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                <ShieldOff size={18} /> Disable 2FA
                            </button>
                        ) : (
                            <button onClick={startSetup} disabled={loading}
                                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                {loading ? <Loader className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
                                Enable 2FA
                            </button>
                        )}
                    </div>
                )}

                {/* ── Setup: QR + OTP ── */}
                {view === 'setup' && (
                    <form onSubmit={handleEnable} className="space-y-5">
                        <div className="text-center">
                            <ShieldCheck className="text-blue-400 mx-auto mb-2" size={24} />
                            <h2 className="text-white font-semibold text-lg">Set up Google Authenticator</h2>
                            <p className="text-gray-400 text-xs mt-1">
                                Scan the QR code with your authenticator app, then enter the 6-digit code.
                            </p>
                        </div>

                        {qrCode && (
                            <div className="flex justify-center">
                                <div className="p-3 bg-white rounded-xl">
                                    <img src={`data:image/png;base64,${qrCode}`} alt="2FA QR Code" className="w-40 h-40" />
                                </div>
                            </div>
                        )}

                        <div>
                            <p className="text-xs text-gray-400 text-center mb-1">Can't scan? Enter this key manually:</p>
                            <div className="flex items-center gap-2 p-2 bg-black/30 border border-white/10 rounded-lg">
                                <code className="flex-1 text-xs text-cyan-400 font-mono tracking-wider break-all">{manualKey}</code>
                                <button type="button" onClick={copyKey}
                                    className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors flex-shrink-0">
                                    {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                                </button>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2 text-center">
                                6-digit code from your app
                            </label>
                            <input ref={otpRef} type="text" inputMode="numeric" value={otp}
                                onChange={handleOtpChange(setOtp)} maxLength={6} required
                                className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-lg text-white text-center text-3xl tracking-[0.5em] font-mono placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="000000" />
                        </div>

                        <div className="flex gap-3">
                            <button type="button" onClick={() => { setError(''); setView('status'); }}
                                className="flex-1 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 rounded-lg transition-colors">
                                Back
                            </button>
                            <button type="submit" disabled={loading || otp.length !== 6}
                                className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                {loading ? <Loader className="animate-spin" size={18} /> : 'Enable 2FA'}
                            </button>
                        </div>
                    </form>
                )}

                {/* ── Backup codes ── */}
                {view === 'backup' && (
                    <div className="space-y-5">
                        <div className="text-center">
                            <CheckCircle className="text-green-400 mx-auto mb-2" size={28} />
                            <h2 className="text-white font-semibold text-lg">2FA Enabled!</h2>
                            <p className="text-gray-400 text-sm mt-1">
                                Save these backup codes — each can only be used once.
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                            {backupCodes.map((code, i) => (
                                <div key={i} className="px-3 py-2 bg-black/40 border border-white/10 rounded-lg font-mono text-xs text-cyan-400 text-center tracking-wider">
                                    {code}
                                </div>
                            ))}
                        </div>

                        <button onClick={onClose}
                            className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors">
                            Done — I've saved my codes
                        </button>
                    </div>
                )}

                {/* ── Disable ── */}
                {view === 'disable' && (
                    <form onSubmit={handleDisable} className="space-y-5">
                        <div className="text-center">
                            <ShieldOff className="text-red-400 mx-auto mb-2" size={24} />
                            <h2 className="text-white font-semibold text-lg">Disable 2FA</h2>
                            <p className="text-gray-400 text-xs mt-1">
                                Enter your password and current authenticator code to confirm.
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                                <input type="password" value={disablePassword}
                                    onChange={e => setDisablePassword(e.target.value)} required
                                    className="w-full pl-9 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500"
                                    placeholder="Your account password" />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2 text-center">
                                Authenticator code
                            </label>
                            <input ref={otpRef} type="text" inputMode="numeric" value={disableOtp}
                                onChange={handleOtpChange(setDisableOtp)} maxLength={6} required
                                className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-lg text-white text-center text-3xl tracking-[0.5em] font-mono placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-red-500"
                                placeholder="000000" />
                        </div>

                        <div className="flex gap-3">
                            <button type="button" onClick={() => { setError(''); setView('status'); }}
                                className="flex-1 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 rounded-lg transition-colors">
                                Back
                            </button>
                            <button type="submit" disabled={loading || disableOtp.length !== 6}
                                className="flex-1 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                {loading ? <Loader className="animate-spin" size={18} /> : 'Disable 2FA'}
                            </button>
                        </div>
                    </form>
                )}

            </div>
        </div>
    );
}
