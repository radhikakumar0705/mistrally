import { Eye, EyeOff } from "lucide-react";
import { useId, useState } from "react";

export default function FormField({ label, icon: Icon, type = "text", hint, ...inputProps }) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-zinc-300">
        {label}
      </label>
      <div className="relative">
        {Icon ? (
          <Icon className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
        ) : null}
        <input
          id={id}
          type={isPassword && revealed ? "text" : type}
          className={`input ${Icon ? "pl-10" : ""} ${isPassword ? "pr-10" : ""}`}
          {...inputProps}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setRevealed((r) => !r)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-zinc-500 transition hover:text-zinc-200"
            aria-label={revealed ? "Hide password" : "Show password"}
          >
            {revealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        ) : null}
      </div>
      {hint ? <p className="mt-1.5 text-xs text-zinc-500">{hint}</p> : null}
    </div>
  );
}
