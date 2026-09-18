"use client";

import { useVoiceRecorder } from "@/lib/useVoiceRecorder";
import { MicIcon } from "@/components/shell/icons";

export default function MicButton({ onTranscribed, className = "" }: { onTranscribed: (text: string) => void; className?: string }) {
  const { state, toggle } = useVoiceRecorder(onTranscribed);

  const label =
    state === "recording" ? "Stop recording" : state === "transcribing" ? "Transcribing…" : state === "error" ? "Mic unavailable" : "Record voice message";

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={state === "transcribing"}
      title={label}
      aria-label={label}
      className={`tap-target flex items-center justify-center rounded-lg border transition-colors disabled:opacity-50 ${
        state === "recording"
          ? "border-danger bg-danger-light text-danger animate-pulse"
          : state === "error"
            ? "border-danger text-danger"
            : "border-border text-ink-secondary hover:border-brand hover:text-brand-dark"
      } ${className}`}
    >
      <MicIcon className="w-4 h-4" />
    </button>
  );
}
