"use client";

import { useEffect, useState } from "react";

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase();
}

interface TeamLogoProps {
  name: string;
  size?: number;
}

export default function TeamLogo({ name, size = 40 }: TeamLogoProps) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    const encoded = encodeURIComponent(name);
    fetch(
      `https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=${encoded}`,
    )
      .then((r) => r.json())
      .then((data) => {
        const badge: string | undefined = data?.teams?.[0]?.strTeamBadge;
        if (badge) setSrc(badge);
      })
      .catch(() => {});
  }, [name]);

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        width={size}
        height={size}
        className="rounded-full object-contain"
        onError={() => setSrc(null)}
      />
    );
  }

  return (
    <div
      className="rounded-full bg-[#272a31] flex items-center justify-center text-[#c8f000] font-bold"
      style={{ width: size, height: size, fontSize: size * 0.3 }}
    >
      {getInitials(name)}
    </div>
  );
}
