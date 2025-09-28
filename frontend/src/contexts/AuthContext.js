import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const verifyToken = async (token) => {
    try {
      const response = await axios.get('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      return { valid: true, user: response.data };
    } catch (error) {
      console.error('Token verification failed:', error.response?.status);
      return { valid: false, user: null };
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        const result = await verifyToken(token);
        if (result.valid) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          setIsAuthenticated(true);
          setUser(result.user);
        } else {
          // Token is invalid, remove it
          localStorage.removeItem('token');
          delete axios.defaults.headers.common['Authorization'];
          setIsAuthenticated(false);
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username, password) => {
    try {
      // Create form data for OAuth2PasswordRequestForm compatibility
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      console.log('DEBUG: Sending login request:', {
        username,
        passwordLength: password.length,
        formData: formData.toString(),
        contentType: 'application/x-www-form-urlencoded'
      });

      const response = await axios.post('/api/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      console.log('DEBUG: Login successful, received token');
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Fetch user data after successful login
      try {
        const userResponse = await axios.get('/api/auth/me', {
          headers: {
            'Authorization': `Bearer ${access_token}`
          }
        });
        setUser(userResponse.data);
      } catch (userError) {
        console.error('Failed to fetch user data:', userError);
        // Don't fail login if user data fetch fails, just log it
      }

      setIsAuthenticated(true);

      return { success: true };
    } catch (error) {
      console.error('DEBUG: Login failed:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setIsAuthenticated(false);
    setUser(null);
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};