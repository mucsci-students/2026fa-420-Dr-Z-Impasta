/**
 * Light and dark themes.
 *
 * The choice is "system" (match the computer's setting), "light", or "dark", and this
 * browser remembers it. The colors live in styles/tokens.css, keyed on data-theme on
 * <html>, which is always "light" or "dark".
 *
 * index.html sets data-theme with a small inline script before the page draws, so a dark
 * page never flashes white while the app loads. Keep STORAGE_KEY the same in both places.
 */
import { useEffect, useState } from "react";

export const STORAGE_KEY = "zimpasta-theme";
const CHOICES = ["system", "light", "dark"];
const darkQuery = window.matchMedia?.("(prefers-color-scheme: dark)") ?? null;

/** The saved choice, or "system" when nothing (or nothing valid) is saved. */
function readChoice() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return CHOICES.includes(saved) ? saved : "system";
  } catch {
    return "system"; // storage blocked (some private windows): follow the system
  }
}

/** Remember a choice in this browser. "system" is the default, so it is stored as nothing. */
function saveChoice(choice) {
  try {
    if (choice === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Storage blocked: the choice still applies until the page is reloaded.
  }
}

/**
 * The theme choice, a way to change it, and the theme showing now ("light" or "dark").
 * With "system", the page follows the computer's setting as it changes, without a reload.
 */
export function useTheme() {
  const [choice, setChoice] = useState(readChoice);
  const [systemDark, setSystemDark] = useState(() => darkQuery?.matches ?? false);

  useEffect(() => {
    if (!darkQuery) return undefined;
    const onChange = (event) => setSystemDark(event.matches);
    darkQuery.addEventListener("change", onChange);
    return () => darkQuery.removeEventListener("change", onChange);
  }, []);

  const theme = choice === "system" ? (systemDark ? "dark" : "light") : choice;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  /** Switch to `next` and remember it. */
  function choose(next) {
    saveChoice(next);
    setChoice(next);
  }

  return { choice, theme, choose };
}
