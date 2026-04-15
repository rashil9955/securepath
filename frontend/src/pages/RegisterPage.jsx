import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';
import {
    Mail, Lock, AlertCircle, Loader, CheckCircle,
    ShieldCheck, Copy, Check, ArrowRight
} from 'lucide-react';

// ── Step indicator ────────────────────────────────────────────────────────────
function StepIndicator({ current }) {
    const steps = ['Account', 'Authenticator', 'Backup Codes'];
    return (
        <div className="flex items-center justify-center gap-2 mb-8">
            {steps.map((label, i) => {
                const idx = i + 1;
                const done = current > idx;
                const active = current === idx;
                return (
                    <React.Fragment key={label}>
                        <div className="flex flex-col items-center gap-1">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${
                                done    ? 'bg-green-500 border-green-500 text-white' :
                                active  ? 'bg-blue-500 border-blue-500 text-white' :
                                          'border-white/20 text-gray-500'
                            }`}>
                                {done ? <Check size={14} /> : idx}
                            </div>
                            <span className={`text-xs ${active ? 'text-white' : 'text-gray-500'}`}>{label}</span>
                        </div>
                        {i < steps.length - 1 && (
                            <div className={`flex-1 h-px mb-5 ${done ? 'bg-green-500' : 'bg-white/10'}`} />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}

export default function RegisterPage() {
    // Step: 1=credentials, 2=qrcode, 3=backupcodes
    const [step, setStep] = useState(1);

    // Step 1
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    // Step 2
    const [qrCode, setQrCode] = useState('');
    const [manualKey, setManualKey] = useState('');
    const [otp, setOtp] = useState('');
    const [copied, setCopied] = useState(false);
    const otpRef = useRef(null);

    // Step 3
    const [backupCodes, setBackupCodes] = useState([]);
    const [savedCodes, setSavedCodes] = useState(false);

    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const { register, isAuthenticated, checkAuth } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (isAuthenticated && step === 1) navigate('/dashboard');
    }, [isAuthenticated, navigate, step]);

    useEffect(() => {
        if (step === 2 && otpRef.current) otpRef.current.focus();
    }, [step]);

    // ── Step 1: Create account → auto-trigger 2FA setup ────────────────────
    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');
        if (password !== confirmPassword) { setError('Passwords do not match'); return; }
        if (password.length < 8)          { setError('Password must be at least 8 characters'); return; }
        if (password.length > 72)         { setError('Password cannot be longer than 72 characters'); return; }

        setLoading(true);
        try {
            const result = await register(email, password, confirmPassword);
            if (!result.success) { setError(result.error || 'Registration failed'); return; }

            // Account created — immediately start 2FA setup
            const setup = await authService.setup2FA();
            setQrCode(setup.qr_code);
            setManualKey(setup.manual_key);
            setStep(2);
        } catch (err) {
            setError(err.message || 'An unexpected error occurred');
        } finally {
            setLoading(false);
        }
    };

    // ── Step 2: Verify first OTP ────────────────────────────────────────────
    const handleEnable = async (e) => {
        e.preventDefault();
        setError('');
        if (!/^\d{6}$/.test(otp)) { setError('Enter the 6-digit code from your app'); return; }

        setLoading(true);
        try {
            const result = await authService.enable2FA(otp);
            setBackupCodes(result.backup_codes || []);
            setStep(3);
        } catch (err) {
            setError(err.message || 'Invalid code — try again');
            setOtp('');
        } finally {
            setLoading(false);
        }
    };

    const copyManualKey = () => {
        navigator.clipboard.writeText(manualKey);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleOtpChange = (e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6));

    const passwordRequirements = [
        { met: password.length >= 8,  text: 'At least 8 characters' },
        { met: password.length <= 72, text: 'Maximum 72 characters' },
    ];

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="bg-white/10 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-8">

                    <div className="text-center mb-2">
                        <h1 className="text-2xl font-bold text-white">Create Account</h1>
                        <p className="text-gray-400 text-sm mt-1">Sign up for SecurePath</p>
                    </div>

                    <StepIndicator current={step} />

                    {error && (
                        <div className="mb-5 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                            <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={18} />
                            <p className="text-red-400 text-sm">{error}</p>
                        </div>
                    )}

                    {/* ── Step 1: Email + Password ── */}
                    {step === 1 && (
                        <form onSubmit={handleRegister} className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                                    <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                                        className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="you@example.com" />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                                    <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                                        className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="••••••••" />
                                </div>
                                {password && (
                                    <div className="mt-2 space-y-1">
                                        {passwordRequirements.map((r, i) => (
                                            <div key={i} className="flex items-center gap-2 text-xs">
                                                {r.met ? <CheckCircle className="text-green-400" size={13} /> : <div className="w-3 h-3 rounded-full border-2 border-gray-500" />}
                                                <span className={r.met ? 'text-green-400' : 'text-gray-400'}>{r.text}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                                    <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required
                                        className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="••••••••" />
                                </div>
                                {confirmPassword && password !== confirmPassword && (
                                    <p className="mt-1 text-xs text-red-400">Passwords do not match</p>
                                )}
                            </div>

                            <button type="submit" disabled={loading}
                                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                {loading ? <><Loader className="animate-spin" size={18} /> Creating account...</> : 'Continue'}
                            </button>

                            <p className="text-center text-gray-400 text-sm">
                                Already have an account?{' '}
                                <a href="/login" className="text-blue-400 hover:text-blue-300 font-semibold">Sign in</a>
                            </p>
                        </form>
                    )}

                    {/* ── Step 2: QR Code + OTP ── */}
                    {step === 2 && (
                        <form onSubmit={handleEnable} className="space-y-5">
                            <div className="text-center">
                                <div className="flex justify-center mb-3">
                                    <ShieldCheck className="text-blue-400" size={28} />
                                </div>
                                <p className="text-white font-medium">Set up Google Authenticator</p>
                                <p className="text-gray-400 text-xs mt-1">
                                    Scan the QR code with your authenticator app, then enter the 6-digit code below.
                                </p>
                            </div>

                            {/* QR Code */}
                            {qrCode && (
                                <div className="flex justify-center">
                                    <div className="p-3 bg-white rounded-xl">
                                        <img
                                            src={`data:image/png;base64,${qrCode}`}
                                            alt="2FA QR Code"
                                            className="w-44 h-44"
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Manual key fallback */}
                            <div>
                                <p className="text-xs text-gray-400 text-center mb-2">Can't scan? Enter this key manually:</p>
                                <div className="flex items-center gap-2 p-2 bg-black/30 border border-white/10 rounded-lg">
                                    <code className="flex-1 text-xs text-cyan-400 font-mono tracking-wider break-all">
                                        {manualKey}
                                    </code>
                                    <button type="button" onClick={copyManualKey}
                                        className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors flex-shrink-0">
                                        {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                                    </button>
                                </div>
                            </div>

                            {/* OTP input */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2 text-center">
                                    Enter the 6-digit code from your app
                                </label>
                                <input
                                    ref={otpRef}
                                    type="text"
                                    inputMode="numeric"
                                    value={otp}
                                    onChange={handleOtpChange}
                                    maxLength={6}
                                    required
                                    className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-lg text-white text-center text-3xl tracking-[0.5em] font-mono placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="000000"
                                />
                            </div>

                            <button type="submit" disabled={loading || otp.length !== 6}
                                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                {loading ? <><Loader className="animate-spin" size={18} /> Verifying...</> : 'Verify & Enable 2FA'}
                            </button>
                        </form>
                    )}

                    {/* ── Step 3: Backup Codes ── */}
                    {step === 3 && (
                        <div className="space-y-5">
                            <div className="text-center">
                                <CheckCircle className="text-green-400 mx-auto mb-3" size={36} />
                                <p className="text-white font-semibold text-lg">2FA is enabled!</p>
                                <p className="text-gray-400 text-sm mt-1">
                                    Save these backup codes somewhere safe. Each one can only be used once
                                    — they're your only way in if you lose your phone.
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                {backupCodes.map((code, i) => (
                                    <div key={i}
                                        className="px-3 py-2 bg-black/40 border border-white/10 rounded-lg font-mono text-sm text-cyan-400 text-center tracking-wider">
                                        {code}
                                    </div>
                                ))}
                            </div>

                            <label className="flex items-start gap-3 cursor-pointer">
                                <input type="checkbox" checked={savedCodes} onChange={e => setSavedCodes(e.target.checked)}
                                    className="mt-1 accent-blue-500" />
                                <span className="text-sm text-gray-300">
                                    I've saved my backup codes in a secure location
                                </span>
                            </label>

                            <button
                                disabled={!savedCodes}
                                onClick={async () => { await checkAuth(); navigate('/dashboard'); }}
                                className="w-full py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2">
                                Go to Dashboard <ArrowRight size={18} />
                            </button>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
