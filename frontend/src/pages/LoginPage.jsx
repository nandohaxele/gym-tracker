// LoginPage - hosts the LoginForm and a link to /register.

import { Link } from 'react-router-dom';
import LoginForm from '../components/auth/LoginForm.jsx';

export default function LoginPage() {
  // TODO: Center the form, mobile-first container, link to register page.
  return (
    <main className="page page--auth">
      <h1>Sign in</h1>
      <LoginForm />
      <p>
        New here? <Link to="/register">Create an account</Link>
      </p>
    </main>
  );
}
