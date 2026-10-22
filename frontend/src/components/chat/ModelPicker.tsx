import { Check, ChevronDown, Cpu } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Props {
  models: string[];
  value: string | null;
  onChange: (model: string) => void;
  disabled?: boolean;
}

export default function ModelPicker({ models, value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onEscape = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  const options = models.length ? models : value ? [value] : [];

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        disabled={disabled || options.length === 0}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-1.5 text-sm text-zinc-200 transition hover:border-white/20 hover:bg-white/[0.06] disabled:opacity-50"
      >
        <Cpu className="h-4 w-4 text-violet-300" />
        <span className="max-w-[9rem] truncate sm:max-w-[14rem]">{value || "Model"}</span>
        <ChevronDown className={`h-4 w-4 text-zinc-500 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open ? (
        <ul
          role="listbox"
          className="glass absolute right-0 z-30 mt-2 max-h-72 w-64 overflow-y-auto rounded-xl p-1 shadow-2xl shadow-black/50"
        >
          <li className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-zinc-500">Local models</li>
          {options.map((model) => (
            <li key={model}>
              <button
                type="button"
                role="option"
                aria-selected={model === value}
                onClick={() => {
                  onChange(model);
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm text-zinc-200 transition hover:bg-white/10"
              >
                <span className="truncate">{model}</span>
                {model === value ? <Check className="h-4 w-4 text-violet-300" /> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
