import { Check, Copy } from "lucide-react";
import { useState } from "react";

interface Props {
  getText: () => string;
  label?: string;
  className?: string;
}

export default function CopyButton({ getText, label = "Copy", className = "icon-btn" }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(getText());
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked (e.g. insecure context); nothing useful to do
    }
  };

  return (
    <button type="button" onClick={copy} className={className} title={copied ? "Copied" : label} aria-label={label}>
      {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
    </button>
  );
}
