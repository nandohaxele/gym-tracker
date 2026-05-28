// LoginForm - email + password, calls AuthContext.login.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../../hooks/useAuth.js';

export default function LoginForm() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    // TODO:
    //   setLoading(true);
    //   try { await auth.login({ email, password }); navigate('/home'); }
    //   catch (err) { setError(err.message); }
    //   finally { setLoading(false); }
  };

  return (
    <form className="form" onSubmit={onSubmit} noValidate>
      {/* TODO: Replace with <Input> components. */}
      <label>Email</label>
      <input
        type="email"
        value={email}
        autoComplete="email"
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <label>Password</label>
      <input
        type="password"
        value={password}
        autoComplete="current-password"
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <p className="form__error">{error}</p>}
      <button type="submit" className="btn btn--primary" disabled={loading}>
        {loading ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  );
}
