export function Sparkline({
  points,
  labels,
  height = 44,
  ariaLabel = "trend",
}: {
  points: number[];
  labels?: string[];
  height?: number;
  ariaLabel?: string;
}) {
  const width = 220;
  const n = points.length;
  const max = Math.max(1, ...points);
  const coords = points.map((p, i) => {
    const x = n <= 1 ? width / 2 : (i / (n - 1)) * width;
    const y = height - 2 - (p / max) * (height - 4);
    return [x, y] as const;
  });
  const line = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = coords[coords.length - 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-11 w-full text-primary"
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel}
    >
      {n > 1 && <polyline points={line} fill="none" stroke="currentColor" strokeWidth="1.5" />}
      {last && <circle cx={last[0]} cy={last[1]} r="2.5" fill="currentColor" />}
      {labels && <title>{labels[labels.length - 1]}</title>}
    </svg>
  );
}
