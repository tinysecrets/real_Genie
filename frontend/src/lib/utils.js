import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

/**
 * Compose multiple class-name inputs into a single Tailwind-compatible class string.
 *
 * Accepts strings, arrays, objects (as conditional maps), and other clsx-style values, then composes them and resolves conflicting Tailwind utility classes.
 * @param {...any} inputs - One or more class-name inputs (strings, arrays, objects, conditional values).
 * @returns {string} The resulting merged class string with Tailwind conflicts resolved.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
