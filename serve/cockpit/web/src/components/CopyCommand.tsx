import { PIcon, useToastManager } from "@porsche-design-system/components-react";
import { type MouseEvent, useEffect, useId, useRef, useState } from "react";

interface CopyCommandProps {
  command: string;
  className?: string;
  /** Visible control label; the copied text stays the exact command. */
  label?: string;
  helper?: string;
}

export type CopyState = "idle" | "copied" | "failed";

export function useCopyToClipboard() {
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const resetTimer = useRef<number | null>(null);
  const { addMessage } = useToastManager();

  useEffect(
    () => () => {
      if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    },
    [],
  );

  const copy = async (value: string, messages: { success: string; failure: string }): Promise<boolean> => {
    let copied = false;
    try {
      await navigator.clipboard.writeText(value);
      setCopyState("copied");
      addMessage({ text: messages.success, state: "success" });
      copied = true;
    } catch {
      setCopyState("failed");
      addMessage({ text: messages.failure, state: "error" });
    }
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => setCopyState("idle"), 1_500);
    return copied;
  };

  return { copyState, copy };
}

export default function CopyCommand({ command, className = "", label, helper }: CopyCommandProps) {
  const { copyState, copy } = useCopyToClipboard();
  const helperId = useId();
  const stateIcon = copyState === "copied" ? "check" : copyState === "failed" ? "error" : null;
  const subject = label ? label.replace(/^Copy /, "").toLowerCase() : command;

  const copyCommand = async (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    await copy(command, {
      success: `Copied ${subject}`,
      failure: `Could not copy ${subject}`,
    });
  };

  if (label) {
    return (
      <span className={["relative z-[1] inline-grid max-w-full gap-1 align-middle", className].join(" ")}>
        <button
          type="button"
          className={[
            "inline-flex w-fit max-w-full cursor-copy items-center gap-1 rounded-sm border border-contrast-low",
            "bg-surface px-static-xs py-1 text-left text-xs font-semibold leading-5 focus-visible:outline-2",
            "focus-visible:outline-offset-2 focus-visible:outline-focus",
            copyState === "copied" ? "text-success" : copyState === "failed" ? "text-error" : "text-primary",
          ].join(" ")}
          aria-describedby={helper ? helperId : undefined}
          title={
            copyState === "copied" ? `Copied ${subject}` : copyState === "failed" ? `Could not copy ${subject}` : label
          }
          onClick={(event) => void copyCommand(event)}
        >
          <PIcon className="shrink-0" name="copy" size="inherit" color="inherit" aria-hidden="true" />
          <span>{label}</span>
          {stateIcon ? (
            <PIcon className="shrink-0" name={stateIcon} size="inherit" color="inherit" aria-hidden="true" />
          ) : null}
        </button>
        {helper ? (
          <span id={helperId} className="text-xs text-contrast-medium">
            {helper}
          </span>
        ) : null}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={[
        "relative z-[1] inline-flex max-w-full cursor-copy items-start gap-1 border-0 bg-transparent",
        "p-0 align-middle text-left text-[0.8125rem] leading-5 focus-visible:outline-2",
        "focus-visible:outline-offset-2 focus-visible:outline-focus",
        copyState === "copied"
          ? "text-success"
          : copyState === "failed"
            ? "text-error"
            : "text-contrast-medium hover:text-primary",
        className,
      ].join(" ")}
      aria-label={`Copy command ${command}`}
      title={
        copyState === "copied"
          ? `Copied ${command}`
          : copyState === "failed"
            ? `Could not copy ${command}`
            : `Copy ${command}`
      }
      onClick={(event) => void copyCommand(event)}
    >
      <PIcon className="shrink-0" name="ai-code" size="inherit" color="inherit" aria-hidden="true" />
      <code className="min-w-0 max-w-full break-words text-inherit leading-5">{command}</code>
      {stateIcon ? (
        <PIcon className="shrink-0" name={stateIcon} size="inherit" color="inherit" aria-hidden="true" />
      ) : null}
    </button>
  );
}
