import React, { useState } from 'react';
import { Lock, ShieldCheck, X, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { authService } from '../services/authService';

export default function ChangePasswordModal({ onClose }) {
    const [currentPassword, setCurrentPassword] = useState('');
    const [otp, setOtp] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    const passwordsMatch = newPassword && confirmPassword && newPassword === confirmPassword;
    const canSubmit = currentPassword && otp.length === 6 && newPassword.length >= 8 && passwordsMatch;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (!passwordsMatch) { setError('New passwords do not match.'); return; }
        setLoading(true);
        try {
            await authService.changePassword(currentPassword, otp, newPassword, confirmPassword);
            setSuccess(true);
        } catch (err) {
            setError(err.message || 'Password change failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-gray-900 border border-white/20 rounded-2xl shadow-2xl w-full max-w-md p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/20 rounded-lg">
                            <Lock className="text-blue-400" size={20} />
                        </div>
                        <h2 className="text-lg font-semibold text-white">Change Password</h2>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {success ? (
                    <div className="text-center py-4">
                        <div className="flex justify-center mb-4">
                            <div className="p-3 bg-green-500/20 rounded-full">
                                <CheckCircle className="text-green-400" size={36} />
                            </div>
                        </div>
                        <p className="text-white font-semibold mb-2">Password changed!</p>
                        <p className="text-gray-400 text-sm mb-6">Your password has been updated successfully.</p>
                        <button
                            onClick={onClose}
                            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                        >
                            Done
                        </button>
                    </div>
                ) : (
                    <>
                        {error && (
                            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2">
                                <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={16} />
                                <p className="text-red-400 text-sm">{error}</p>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1.5">Current Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                                    <input
                                        type="password"
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        required
                                        className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                        placeholder="Your current password"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                                    Authenticator Code
                                </label>
                                <div className="relative">
                                    <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        value={otp}
                                        onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                        required
                                        maxLength={6}
                                        className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm font-mono tracking-widest"
                                        placeholder="000000"
                                    />
                                </div>
                                <p className="mt-1 text-xs text-gray-500">6-digit code from your authenticator app</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1.5">New Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                                    <input
                                        type="password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        required
                                        minLength={8}
                                        className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                        placeholder="At least 8 characters"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1.5">Confirm New Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                                    <input
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        required
                                        className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                        placeholder="Repeat new password"
                                    />
                                </div>
                                {confirmPassword && !passwordsMatch && (
                                    <p className="mt-1 text-xs text-red-400">Passwords don't match</p>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={loading || !canSubmit}
                                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 text-sm mt-2"
                            >
                                {loading ? <><Loader className="animate-spin" size={16} /> Saving...</> : 'Change Password'}
                            </button>
                        </form>
                    </>
                )}
            </div>
        </div>
    );
}
