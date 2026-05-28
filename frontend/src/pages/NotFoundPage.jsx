// NotFoundPage - simple 404.

import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  // TODO: Friendly 404 with a back-to-home link.
  return (
    <main className="page page--center">
      <h1>404</h1>
      <p>Page not found.</p>
      <Link to="/home" className="btn btn--primary">Back to Home</Link>
    </main>
  );
}
