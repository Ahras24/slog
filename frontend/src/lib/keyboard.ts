import type { KeyboardEvent } from "react";

const ENTER_FIELDS_SELECTOR = "[data-enter-field]";

export function focusNextEnterField(
  event: KeyboardEvent<HTMLElement>,
  container: HTMLElement | null,
  onLastField?: () => void
) {
  if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return;

  const target = event.target as HTMLElement;
  if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") return;

  const fields = Array.from(container?.querySelectorAll<HTMLElement>(ENTER_FIELDS_SELECTOR) ?? []).filter(
    (field) => !field.hasAttribute("disabled") && field.getAttribute("aria-disabled") !== "true"
  );
  const currentIndex = fields.indexOf(target);
  if (currentIndex < 0) return;

  event.preventDefault();
  const nextField = fields[currentIndex + 1];
  if (nextField) {
    nextField.focus();
  } else {
    onLastField?.();
  }
}
