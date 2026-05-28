// RegisterPage - hosts the RegisterForm and a link back to /login.

import { Link } from 'react-router-dom';
import RegisterForm from '../components/auth/RegisterForm.jsx';

export default function RegisterPage() {
  // TODO: Same layout as LoginPage; on success route to /home.
  return (
    <main className="page page--auth">
      <h1>Create account</h1>
      <RegisterForm />
      <p>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </main>
  );
}
