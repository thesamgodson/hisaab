/** "View Source" link pointing to the government portal where data originated. */

interface SourceLinkProps {
  url: string;
  label?: string;
}

export default function SourceLink({
  url,
  label = "Official source",
}: SourceLinkProps) {
  if (!url) return null;
  const href = url.startsWith("http") ? url : `https://${url}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="source-link"
    >
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
        />
      </svg>
      {label}
    </a>
  );
}
