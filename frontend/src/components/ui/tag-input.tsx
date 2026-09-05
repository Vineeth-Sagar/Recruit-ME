"use client";

import { X } from "lucide-react";
import { useState, type KeyboardEvent } from "react";

import { cn } from "@/lib/utils";

export function TagInput({
  value,
  onChange,
  placeholder,
  id,
}: {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  id?: string;
}) {
  const [draft, setDraft] = useState("");

  function commit(raw: string) {
    const parts = raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .filter((s) => !value.includes(s));
    if (parts.length) onChange([...value, ...parts]);
    setDraft("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit(draft);
    } else if (e.key === "Backspace" && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  }

  return (
    <div
      className={cn(
        "flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-transparent px-2 py-1.5 text-sm shadow-sm focus-within:ring-1 focus-within:ring-ring",
      )}
    >
      {value.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-xs text-secondary-foreground"
        >
          {tag}
          <button
            type="button"
            aria-label={`Remove ${tag}`}
            onClick={() => onChange(value.filter((t) => t !== tag))}
            className="rounded-sm hover:text-destructive"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      <input
        id={id}
        className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground min-w-24"
        value={draft}
        placeholder={value.length ? "" : placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={() => draft && commit(draft)}
      />
    </div>
  );
}
