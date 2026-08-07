interface SourceLinkProps {
  url: string;
  label?: string;
  accessibleLabel?: string;
}

export default function SourceLink({ url, label = "Data source", accessibleLabel }: SourceLinkProps) {
  if (!url) return null;
  const href = url.startsWith("http") ? url : `https://${url}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="source-link"
      aria-label={accessibleLabel}
    >
      {label}<span className="sr-only"> (opens source in a new tab)</span>
    </a>
  );
}
