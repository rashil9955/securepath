import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // Check if user is authenticated on mount
    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        try {
            const userData = await authService.getCurrentUser();
            setUser(userData);
        } catch (error) {
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    const login = async (email, password) => {
        try {
            const data = await authService.login(email, password);
            if (data.requires_2fa) {
                // Password was correct but 2FA is needed — don't log the user in yet
                return { success: false, requires2FA: true, twoFaToken: data.two_fa_token };
            }
            setUser(data.user);
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message || 'Login failed' };
        }
    };

    const verify2FA = async (twoFaToken, otp) => {
        try {
            const data = await authService.verify2FA(twoFaToken, otp);
            setUser(data.user);
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message || 'Invalid code. Try again.' };
        }
    };

    const register = async (email, password, confirmPassword) => {
        try {
            const data = await authService.register(email, password, confirmPassword);
            // Do NOT call setUser here — the user must complete mandatory 2FA setup
            // before gaining access to the dashboard. The access token is stored in
            // localStorage by authService so subsequent API calls (setup2FA, enable2FA)
            // still work.
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message || 'Registration failed' };
        }
    };

    const logout = async () => {
        try {
            await authService.logout();
            setUser(null);
            navigate('/login');
        } catch (error) {
            console.error('Logout error:', error);
            // Clear user state even if logout fails
            setUser(null);
            navigate('/login');
        }
    };

    const value = {
        user,
        loading,
        login,
        verify2FA,
        register,
        logout,
        isAuthenticated: !!user,
        checkAuth
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

