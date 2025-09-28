import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
  const { t } = useTranslation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated } = useAuth();

  // Clear form when login is successful
  useEffect(() => {
    if (isAuthenticated) {
      setUsername('');
      setPassword('');
      setError('');
    }
  }, [isAuthenticated]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(username, password);

    if (!result.success) {
      setError(result.error);
      setLoading(false);
    }
    // If successful, isAuthenticated will become true and trigger the useEffect above
  };

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white neon-cyan">{t('login.app_name')}</h2>
          <p className="mt-2 text-sm text-dark-400">{t('login.sign_in_access')}</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-dark-300">
                {t('login.username')}
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="mt-1 block w-full px-3 py-2 border border-dark-600 rounded-md shadow-sm bg-dark-800 text-white placeholder-dark-400 focus:outline-none focus:ring-accent-cyan focus:border-accent-cyan"
                placeholder={t('login.enter_username')}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-dark-300">
                {t('login.password')}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="mt-1 block w-full px-3 py-2 border border-dark-600 rounded-md shadow-sm bg-dark-800 text-white placeholder-dark-400 focus:outline-none focus:ring-accent-cyan focus:border-accent-cyan"
                placeholder={t('login.enter_password')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm text-center">
              {error}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-accent-cyan hover:bg-accent-cyan/80 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-cyan disabled:opacity-50 disabled:cursor-not-allowed neon-cyan"
            >
              {loading ? t('login.signing_in') : t('login.sign_in')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;