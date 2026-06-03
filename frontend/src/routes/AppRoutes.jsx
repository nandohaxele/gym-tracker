// Application route table.
// Public-only routes: /login, /register (authed users are bounced to /home).
// Protected routes: everything else, wrapped in <ProtectedRoute> + <AppShell>.

import { Routes, Route, Navigate } from 'react-router-dom';

import ProtectedRoute from './ProtectedRoute.jsx';
import PublicRoute from './PublicRoute.jsx';
import AppShell from '@/components/layout/AppShell.jsx';

import LoginPage from '@/pages/LoginPage.jsx';
import RegisterPage from '@/pages/RegisterPage.jsx';
import HomePage from '@/pages/HomePage.jsx';
import WorkoutEditorPage from '@/pages/WorkoutEditorPage.jsx';
import WorkoutDetailPage from '@/pages/WorkoutDetailPage.jsx';
import NotFoundPage from '@/pages/NotFoundPage.jsx';

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public (auth) routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />

      {/* Protected app routes */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/home" replace />} />
        <Route path="/home" element={<HomePage />} />
        {/* TODO (Phase 5 Step 2+): real workout list / editor / detail UIs. */}
        <Route path="/workouts/new" element={<WorkoutEditorPage />} />
        <Route path="/workouts/:id" element={<WorkoutDetailPage />} />
        <Route path="/workouts/:id/edit" element={<WorkoutEditorPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
