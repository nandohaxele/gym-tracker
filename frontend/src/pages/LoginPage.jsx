// LoginPage - centered auth card with the LoginForm and a link to register.

import { Link } from 'react-router-dom';
import AuthCard from '@/components/ui/AuthCard.jsx';
import LoginForm from '@/components/auth/LoginForm.jsx';

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh flex-col justify-center px-4 py-10 pt-safe">
      <div className="mx-auto w-full max-w-sm">
        <AuthCard
          title="Welcome back"
          subtitle="Sign in to track your workouts"
          footer={
            <>
              New here?{' '}
              <Link
                to="/register"
                className="font-semibold text-primary underline-offset-4 hover:underline"
              >
                Create an account
              </Link>
            </>
          }
        >
          <LoginForm />
        </AuthCard>
      </div>
    </main>
  );
}
