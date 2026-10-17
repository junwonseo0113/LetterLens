import { Link } from "react-router-dom";

export default function BigButton({ to, state, onClick, children, variant = "primary", type, ...rest }) {
  const className = `big-button ${variant !== "primary" ? variant : ""}`.trim();

  if (to) {
    return (
      <Link to={to} state={state} className={className} {...rest}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type || "button"} className={className} onClick={onClick} {...rest}>
      {children}
    </button>
  );
}
