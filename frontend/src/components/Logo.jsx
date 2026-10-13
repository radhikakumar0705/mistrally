import { Bot } from "lucide-react";

export function LogoMark({ size = "md" }) {
  const sizes = {
    sm: "h-7 w-7 rounded-lg [&>svg]:h-4 [&>svg]:w-4",
    md: "h-9 w-9 rounded-xl [&>svg]:h-5 [&>svg]:w-5",
    lg: "h-16 w-16 rounded-2xl [&>svg]:h-8 [&>svg]:w-8",
  };
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white shadow-lg shadow-violet-900/40 ${sizes[size]}`}
    >
      <Bot strokeWidth={2.25} />
    </span>
  );
}

export default function Logo({ size = "md" }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark size={size} />
      <span className="text-lg font-semibold tracking-tight text-white">Mistrally</span>
    </span>
  );
}
