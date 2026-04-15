import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, ShieldCheck, Lock, AlertCircle, CheckCircle, Loader, ArrowLeft } from 'lucide-react';
import { authService } from '../services/authService';

// Step indicator (1 → 2 → 3)
function StepIndicator({ current }) {
    const steps = ['Verify Identity', 'New Password', 'Done'];
    return (
        <div className="flex items-center justify-center mb-8 gap-2">
            {steps.map((label, i) => {
                const n = i + 1;
                const done = n < current;
                const active = n === current;
                return (
                    <React.Fragment key={n}>
                        <div className="flex flex-col items-center">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2
                                ${done ? 'bg-green-500 border-green-500 text-white'
                                    : active ? 'bg-blue-500 border-blue-500 text-white'
                                    : 'bg-transparent border-gray-600 text-gray-500'}`}>
                                {done ? <CheckCircle size={16} /> : n}
                            </div>
                            <span className={`text-xs mt-1 ${active ? 'text-white' : 'text-gray-500'}`}>{label}</span>
                        </div>
                        {i < steps.length - 1 && (
                            <div className={`h-px w-10 mb-5 ${done ? 'bg-green-500' : 'bg-gray-600'}`} />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}

export default function ForgotPasswordPage() {
    const navigate = useNavigate();

    // Step 1 state
    const [email, setEmail] = useState('');
    const [otp, setOtp] = useState('');
    const otpRef = useRef(null);

    // Step 2 state
    const [resetToken, setResetToken] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [step, setStep] = useState(1); // 1 | 2 | 3
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (step === 1 && otpRef.current) otpRef.current.focus();
    }, [step]);

    // ── Step 1: verify email + TOTP ──────────────────────────────────────────
    const handleVerify = async (e) => {
        e.preventDefault();
        setError('');
        if (otp.length !== 6) { setError('Enter the 6-digit code from your authenticator app.'); return; }
        setLoading(true);
        try {
            const data = await authService.forgotPasswordVerify(email, otp);
            setResetToken(data.reset_token);
            setStep(2);
        } catch (err) {
            setError(err.message || 'Verification failed.');
            setOtp('');
        } finally {
            setLoading(false);
        }
    };

    // ── Step 2: set new password ─────────────────────────────────────────────
    const handleReset = async (e) => {
        e.preventDefault();
        setError('');
        if (newPassword !== confirmPassword) { setError('Passwords do not match.'); return; }
        if (newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
        setLoading(true);
        try {
            await authService.forgotPasswordReset(resetToken, newPassword, confirmPassword);
            setStep(3);
        } catch (err) {
            setError(err.message || 'Password reset failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="bg-white/10 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-8">
                    <StepIndicator current={step} />

                    {error && (
                        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                            <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
                            <p className="text-red-400 text-sm">{error}</p>
                        </div>
                    )}

                    {/* ── Step 1: Email + TOTP ── */}
                    {step === 1 && (
                        <>
                            <div className="text-center mb-8">
                                <div className="flex justify-center mb-4">
                                    <div className="p-3 bg-blue-500/20 rounded-full">
                                        <ShieldCheck className="text-blue-400" size={32} />
                                    </div>
                                </div>
                                <h1 className="text-2xl font-bold text-white mb-2">Reset Your Password</h1>
                                <p className="text-gray-400 text-sm">
                                    Enter your email and the current code from your authenticator app to verify your identity.
                                </p>
                            </div>

                            <form onSubmit={handleVerify} className="space-y-5">
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                                        <input
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            placeholder="you@example.com"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Authenticator Code</label>
                                    <input
                                        ref={otpRef}
                                        type="text"
                                        inputMode="numeric"
                                        value={otp}
                                        onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                        required
                                        maxLength={6}
                                        className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-lg text-white text-center text-3xl tracking-[0.5em] font-mono placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="000000"
                                    />
                                    <p className="mt-1 text-xs text-gray-500 text-center">6-digit code from Google Authenticator</p>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading || otp.length !== 6 || !email}
                                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                                >
                                    {loading ? <><Loader className="animate-spin" size={20} /> Verifying...</> : 'Verify Identity'}
                                </button>
                            </form>

                            <button
                                onClick={() => navigate('/login')}
                                className="mt-4 w-full flex items-center justify-center gap-2 text-gray-400 hover:text-white text-sm transition-colors"
                            >
                                <ArrowLeft size={16} /> Back to login
                            </button>
                        </>
                    )}

                    {/* ── Step 2: New password ── */}
                    {step === 2 && (
                        <>
                            <div className="text-center mb-8">
                                <div className="flex justify-center mb-4">
                                    <div className="p-3 bg-green-500/20 rounded-full">
                                        <Lock className="text-green-400" size={32} />
                                    </div>
                                </div>
                                <h1 className="text-2xl font-bold text-white mb-2">Set New Password</h1>
                                <p className="text-gray-400 text-sm">Choose a strong password for your account.</p>
                            </div>

                            <form onSubmit={handleReset} className="space-y-5">
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">New Password</label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                                        <input
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            required
                                            minLength={8}
                                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            placeholder="At least 8 characters"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                                        <input
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            placeholder="Repeat your new password"
                                        />
                                    </div>
                                    {confirmPassword && newPassword !== confirmPassword && (
                                        <p className="mt-1 text-xs text-red-400">Passwords don't match</p>
                                    )}
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading || newPassword.length < 8 || newPassword !== confirmPassword}
                                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                                >
                                    {loading ? <><Loader className="animate-spin" size={20} /> Saving...</> : 'Set New Password'}
                                </button>
                            </form>
                        </>
                    )}

                    {/* ── Step 3: Done ── */}
                    {step === 3 && (
                        <div className="text-center">
                            <div className="flex justify-center mb-6">
                                <div className="p-4 bg-green-500/20 rounded-full">
                                    <CheckCircle className="text-green-400" size={48} />
                                </div>
                            </div>
                            <h1 className="text-2xl font-bold text-white mb-3">Password Updated!</h1>
                            <p className="text-gray-400 text-sm mb-8">
                                Your password has been changed successfully. All existing sessions have been signed out.
                            </p>
                            <button
                                onClick={() => navigate('/login')}
                                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                            >
                                Go to Login
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
