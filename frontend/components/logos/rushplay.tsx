export default function RushPlayLogo({
  className,
}: {
  className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        width: 28,
        height: 28,
        borderRadius: 6,
        background: "#C8F000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          color: "#06090F",
          fontWeight: 800,
          fontSize: 16,
          lineHeight: 1,
          fontFamily: "var(--font-heading, sans-serif)",
        }}
      >
        R
      </span>
    </div>
  );
}
