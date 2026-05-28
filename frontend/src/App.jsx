// Root component.
// Currently delegates to AppRoutes; can host global providers/UI shells later.

import AppRoutes from './routes/AppRoutes.jsx';

export default function App() {
  // TODO: Add global toasts / error boundary / loading overlay here if needed.
  return <AppRoutes />;
}
