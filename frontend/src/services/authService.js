import { API_CONFIG } from '../config/constants';

class AuthError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'AuthError';
        this.status = status;
        this.data = data;
    }
}

const apiCall = async (endpoint, options = {}) => {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;

    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        credentials: 'include', // Important for httpOnly cookies
    };

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            let errorData = {};
            try {
                errorData = await response.json();
            } catch (e) {
                throw new AuthError(
                    `Server Error (${response.status}): Failed to parse JSON response.`,
                    response.status,
                    {}
                );
            }

            const errorMessage = errorData.error || errorData.detail || `Server responded with status ${response.status}`;
            throw new AuthError(errorMessage, response.status, errorData);
        }

        return response.json();
    } catch (error) {
        if (error instanceof AuthError) {
            throw error;
        }
        throw new AuthError(error.message || 'Network error occurred', 0, {});
    }
};

export const authService = {
    async register(email, password, confirmPassword) {
        const data = await apiCall('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, confirm_password: confirmPassword }),
        });
        // Store access token in localStorage as fallback for Authorization header
        if (data.access_token) {
            this.setAccessToken(data.access_token);
        }
        return data;
    },

    async login(email, password) {
        const data = await apiCall('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        // If 2FA is required, return the pending token — don't store access_token yet
        if (data.requires_2fa) {
            return data;
        }
        if (data.access_token) {
            this.setAccessToken(data.access_token);
        }
        return data;
    },

    async setup2FA() {
        return apiCall('/2fa/setup', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAccessToken()}` },
        });
    },

    async enable2FA(otp) {
        return apiCall('/2fa/enable', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAccessToken()}` },
            body: JSON.stringify({ otp }),
        });
    },

    async disable2FA(password, otp) {
        return apiCall('/2fa/disable', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getAccessToken()}` },
            body: JSON.stringify({ password, otp }),
        });
    },

    async get2FAStatus() {
        return apiCall('/2fa/status', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${this.getAccessToken()}` },
        });
    },

    async verify2FA(twoFaToken, otp, rememberDevice = false) {
        const data = await apiCall('/2fa/login-verify', {
            method: 'POST',
            body: JSON.stringify({
                two_fa_token: twoFaToken,
                otp,
                remember_device: rememberDevice,
            }),
        });
        if (data.access_token) {
            this.setAccessToken(data.access_token);
        }
        return data;
    },

    async logout() {
        try {
            await apiCall('/auth/logout', {
                method: 'POST',
            });
        } finally {
            // Clear token from localStorage
            this.setAccessToken(null);
        }
    },

    async getCurrentUser() {
        // Try to get token from cookie first, fallback to Authorization header
        const response = await fetch(`${API_CONFIG.BASE_URL}/auth/me`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Authorization': `Bearer ${this.getAccessToken()}`,
            },
        });

        if (!response.ok) {
            throw new AuthError('Not authenticated', response.status);
        }

        return response.json();
    },

    getAccessToken() {
        // Try to get from cookie (browser will handle httpOnly cookies automatically)
        // For Authorization header, we need to store it in memory or localStorage
        // Since we're using httpOnly cookies, we don't need to manually get it
        // But for the Authorization header fallback, check localStorage
        return localStorage.getItem('access_token') || null;
    },

    setAccessToken(token) {
        // Store in localStorage as fallback for Authorization header
        if (token) {
            localStorage.setItem('access_token', token);
        } else {
            localStorage.removeItem('access_token');
        }
    },
};

export default authService;

