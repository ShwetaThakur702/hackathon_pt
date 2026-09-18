"use client";

import { useCallback, useRef, useState } from "react";
import { transcribeAudio } from "@/lib/api";

export type RecorderState = "idle" | "recording" | "transcribing" | "error";

/** Records mic audio via MediaRecorder, uploads it to POST
 * /api/voice/transcribe on stop, and hands the transcribed text back via
 * `onTranscribed`. Voice is optional everywhere it's used — any failure
 * (permission denied, no mic, transcription error) just resets to idle so
 * the customer can type instead; nothing else breaks. */
export function useVoiceRecorder(onTranscribed: (text: string) => void) {
  const [state, setState] = useState<RecorderState>("idle");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setState("transcribing");
        try {
          const result = await transcribeAudio(blob);
          if (result.text) onTranscribed(result.text);
          setState("idle");
        } catch (err) {
          console.error("Transcription failed", err);
          setState("error");
          setTimeout(() => setState("idle"), 2000);
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setState("recording");
    } catch (err) {
      console.error("Microphone unavailable", err);
      setState("error");
      setTimeout(() => setState("idle"), 2000);
    }
  }, [onTranscribed]);

  const stop = useCallback(() => {
    mediaRecorderRef.current?.stop();
  }, []);

  const toggle = useCallback(() => {
    if (state === "recording") stop();
    else if (state === "idle") start();
  }, [state, start, stop]);

  return { state, toggle };
}
