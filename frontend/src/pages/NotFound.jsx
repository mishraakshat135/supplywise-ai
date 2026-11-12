import { Link } from "react-router-dom";
export default function NotFound() {
  return (
    <div className="not-found">
      <span>404</span>
      <h1>Page not found</h1>
      <p>The page you’re looking for isn’t in this workspace.</p>
      <Link className="button primary" to="/">
        Return to dashboard
      </Link>
    </div>
  );
}
