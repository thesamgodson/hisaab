/** Red flag indicator shown on scheme cards when data has issues or values are alarming. */

interface RedFlagBadgeProps {
  label: string;
}

export default function RedFlagBadge({ label }: RedFlagBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-md"
      style={{
        background: "oklch(0.95 0.03 25)",
        color: "oklch(0.45 0.16 25)",
      }}
    >
      <svg
        className="w-3 h-3"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>
      {label}
    </span>
  );
}
