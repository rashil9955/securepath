import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Mail, Lock, AlertCircle, Loader, ShieldCheck, ArrowLeft } from 'lucide-react';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [otp, setOtp] = useState('');
    const [twoFaToken, setTwoFaToken] = useState('');
    const [step, setStep] = useState('password'); // 'password' | 'otp'
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const otpRef = useRef(null);

    const { login, verify2FA, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (isAuthenticated) navigate('/dashboard');
    }, [isAuthenticated, navigate]);

    // Auto-focus OTP field when step changes
    useEffect(() => {
        if (step === 'otp' && otpRef.current) {
            otpRef.current.focus();
        }
    }, [step]);

    const handlePasswordSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const result = await login(email, password);

            if (result.requires2FA) {
                // Password correct but 2FA needed — switch to OTP step
                setTwoFaToken(result.twoFaToken);
                setStep('otp');
            } else if (result.success) {
                navigate('/dashboard');
            } else {
                setError(result.error || 'Login failed');
            }
        } catch (err) {
            setError(err.message || 'An unexpected error occurred');
        } finally {
            setLoading(false);
        }
    };

    const handleOtpSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
            setError('Please enter the 6-digit code from your authenticator app.');
            return;
        }

        setLoading(true);
        try {
            const result = await verify2FA(twoFaToken, otp);
            if (result.success) {
                navigate('/dashboard');
            } else {
                setError(result.error || 'Invalid code. Please try again.');
                setOtp('');
            }
        } catch (err) {
            setError(err.message || 'Verification failed');
            setOtp('');
        } finally {
            setLoading(false);
        }
    };

    const handleOtpChange = (e) => {
        // Only allow digits, max 6 characters
        const value = e.target.value.replace(/\D/g, '').slice(0, 6);
        setOtp(value);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="bg-white/10 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 p-8">

                    {/* ── Step 1: Password ── */}
                    {step === 'password' && (
                        <>
                            <div className="text-center mb-8">
                                <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
                                <p className="text-gray-400">Sign in to your SecurePath account</p>
                            </div>

                            {error && (
                                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                                    <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
                                    <p className="text-red-400 text-sm">{error}</p>
                                </div>
                            )}

                            <form onSubmit={handlePasswordSubmit} className="space-y-6">
                                <div>
                                    <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                        Email Address
                                    </label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                                        <input
                                            id="email"
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            placeholder="you@example.com"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                                        Password
                                    </label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                                        <input
                                            id="password"
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            placeholder="••••••••"
                                        />
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                                >
                                    {loading ? (
                                        <><Loader className="animate-spin" size={20} /> Signing in...</>
                                    ) : 'Sign In'}
                                </button>
                            </form>

                            <div className="mt-4 text-center">
                                <a href="/forgot-password" className="text-sm text-blue-400 hover:text-blue-300">
                                    Forgot your password?
                                </a>
                            </div>

                            <div className="mt-4 text-center">
                                <p className="text-gray-400">
                                    Don't have an account?{' '}
                                    <a href="/register" className="text-blue-400 hover:text-blue-300 font-semibold">
                                        Sign up
                                    </a>
                                </p>
                            </div>
                        </>
                    )}

                    {/* ── Step 2: OTP ── */}
                    {step === 'otp' && (
                        <>
                            <div className="text-center mb-8">
                                <div className="flex justify-center mb-4">
                                    <div className="p-3 bg-blue-500/20 rounded-full">
                                        <ShieldCheck className="text-blue-400" size={32} />
                                    </div>
                                </div>
                                <h1 className="text-2xl font-bold text-white mb-2">Two-Factor Authentication</h1>
                                <p className="text-gray-400 text-sm">
                                    Open your authenticator app and enter the 6-digit code for{' '}
                                    <span className="text-white font-medium">{email}</span>
                                </p>
                            </div>

                            {error && (
                                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                                    <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
                                    <p className="text-red-400 text-sm">{error}</p>
                                </div>
                            )}

                            <form onSubmit={handleOtpSubmit} className="space-y-6">
                                <div>
                                    <label htmlFor="otp" className="block text-sm font-medium text-gray-300 mb-2">
                                        6-Digit Code
                                    </label>
                                    <input
                                        id="otp"
                                        ref={otpRef}
                                        type="text"
                                        inputMode="numeric"
                                        value={otp}
                                        onChange={handleOtpChange}
                                        required
                                        maxLength={6}
                                        className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-lg text-white text-center text-3xl tracking-[0.5em] font-mono placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="000000"
                                    />
                                    <p className="mt-2 text-xs text-gray-500 text-center">
                                        Code refreshes every 30 seconds
                                    </p>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading || otp.length !== 6}
                                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                                >
                                    {loading ? (
                                        <><Loader className="animate-spin" size={20} /> Verifying...</>
                                    ) : 'Verify & Sign In'}
                                </button>
                            </form>

                            <button
                                onClick={() => { setStep('password'); setError(''); setOtp(''); }}
                                className="mt-4 w-full flex items-center justify-center gap-2 text-gray-400 hover:text-white text-sm transition-colors"
                            >
                                <ArrowLeft size={16} /> Back to login
                            </button>
                        </>
                    )}

                </div>
            </div>
        </div>
    );
}
