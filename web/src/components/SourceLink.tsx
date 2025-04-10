/** "View Source" link pointing to the government portal where data originated. */

interface SourceLinkProps {
  url: string;
  label?: string;
}

export default function SourceLink({
  url,
  label = "View Source",
}: SourceLinkProps) {
  if (!url) return null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
    >
      <svg
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
        />
      </svg>
      {label}
    </a>
  );
}
