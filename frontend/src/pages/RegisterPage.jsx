// RegisterPage - centered auth card with the RegisterForm and a link to login.

import { Link } from 'react-router-dom';
import AuthCard from '@/components/ui/AuthCard.jsx';
import RegisterForm from '@/components/auth/RegisterForm.jsx';

export default function RegisterPage() {
  return (
    <main className="flex min-h-dvh flex-col justify-center px-4 py-10 pt-safe">
      <div className="mx-auto w-full max-w-sm">
        <AuthCard
          title="Create your account"
          subtitle="Start logging your training today"
          footer={
            <>
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-semibold text-primary underline-offset-4 hover:underline"
              >
                Sign in
              </Link>
            </>
          }
        >
          <RegisterForm />
        </AuthCard>
      </div>
    </main>
  );
}
