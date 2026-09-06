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
import StartWorkoutPage from '@/pages/StartWorkoutPage.jsx';
import WorkoutEditorPage from '@/pages/WorkoutEditorPage.jsx';
import WorkoutDetailPage from '@/pages/WorkoutDetailPage.jsx';
import TemplatesPage from '@/pages/TemplatesPage.jsx';
import TemplateDetailPage from '@/pages/TemplateDetailPage.jsx';
import TemplateEditorPage from '@/pages/TemplateEditorPage.jsx';
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
        <Route path="/workouts/new" element={<StartWorkoutPage />} />
        <Route path="/workouts/:id" element={<WorkoutDetailPage />} />
        <Route path="/workouts/:id/edit" element={<WorkoutEditorPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/new" element={<TemplateEditorPage />} />
        <Route path="/templates/:id" element={<TemplateDetailPage />} />
        <Route path="/templates/:id/edit" element={<TemplateEditorPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
