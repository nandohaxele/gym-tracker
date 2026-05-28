// RegisterForm - email + password (+ confirm), calls AuthContext.register.

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../../hooks/useAuth.js';

export default function RegisterForm() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    // TODO:
    //   if (password !== confirm) return setError('Passwords do not match');
    //   setLoading(true);
    //   try { await auth.register({ email, password }); navigate('/home'); }
    //   catch (err) { setError(err.message); }
    //   finally { setLoading(false); }
  };

  return (
    <form className="form" onSubmit={onSubmit} noValidate>
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
        autoComplete="new-password"
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <label>Confirm password</label>
      <input
        type="password"
        value={confirm}
        autoComplete="new-password"
        onChange={(e) => setConfirm(e.target.value)}
        required
      />
      {error && <p className="form__error">{error}</p>}
      <button type="submit" className="btn btn--primary" disabled={loading}>
        {loading ? 'Creating...' : 'Create account'}
      </button>
    </form>
  );
}
