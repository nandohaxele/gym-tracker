// Application route table.
// Public routes: /login, /register
// Protected routes: everything else (wrapped in <ProtectedRoute>).

import { Routes, Route, Navigate } from 'react-router-dom';

import ProtectedRoute from './ProtectedRoute.jsx';
import AppShell from '../components/layout/AppShell.jsx';

import LoginPage from '../pages/LoginPage.jsx';
import RegisterPage from '../pages/RegisterPage.jsx';
import HomePage from '../pages/HomePage.jsx';
import WorkoutEditorPage from '../pages/WorkoutEditorPage.jsx';
import WorkoutDetailPage from '../pages/WorkoutDetailPage.jsx';
import NotFoundPage from '../pages/NotFoundPage.jsx';

export default function AppRoutes() {
  // TODO: Refine route layout / nested routes when more pages exist.
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/home" replace />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/workouts/new" element={<WorkoutEditorPage />} />
        <Route path="/workouts/:id" element={<WorkoutDetailPage />} />
        <Route path="/workouts/:id/edit" element={<WorkoutEditorPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
