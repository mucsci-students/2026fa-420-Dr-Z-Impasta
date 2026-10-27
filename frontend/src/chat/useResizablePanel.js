/**
 * Drag the chat panel's left edge to make it wider or narrower.
 *
 * - Dragging past the narrowest width moves the panel to the right with the pointer;
 *   letting go far enough out closes it (`onDismiss`), otherwise it settles back.
 * - Double-clicking the edge goes back to the default (half the window).
 * - With the keyboard, focus the edge and use ← (wider) and → (narrower).
 * - The width is remembered in this browser.
 */
import { useRef, useState } from "react";

const STORAGE_KEY = "zimpasta-chat-width";
export const MIN_WIDTH = 360; // keep in sync with .chat-panel's min-width in chat.css
const ROOM_FOR_APP = 240; // the panel never covers the whole window (max-width in chat.css)
const KEY_STEP = 32;
const DISMISS_PAST = 120; // dragged this far past the narrowest width: letting go closes

function readWidth() {
  try {
    const saved = Number(localStorage.getItem(STORAGE_KEY));
    return saved >= MIN_WIDTH ? saved : null;
  } catch {
    return null; // storage blocked: use the default width
  }
}

function saveWidth(width) {
  try {
    if (width == null) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, String(Math.round(width)));
  } catch {
    // Storage blocked: the width lasts until the page is reloaded.
  }
}

const maxWidth = () => Math.max(MIN_WIDTH, window.innerWidth - ROOM_FOR_APP);
const clamp = (width) => Math.min(Math.max(width, MIN_WIDTH), maxWidth());

/**
 * `panelRef` is the panel element; `onDismiss` closes it. Returns the panel's inline
 * `style`, `dragging` (whether the edge is being held), `handleProps` for the edge, and
 * `settle()`, which puts a pushed-out panel back in place before it opens again.
 */
export function useResizablePanel(panelRef, onDismiss) {
  const [width, setWidth] = useState(readWidth); // null: the default, half the window
  const [offset, setOffset] = useState(0); // px pushed right, past the narrowest width
  const [dragging, setDragging] = useState(false);
  const drag = useRef(null); // { startWidth } while the edge is held
  const restore = useRef(undefined); // the width to reopen at after being pushed out

  function currentWidth() {
    return width ?? panelRef.current?.getBoundingClientRect().width ?? MIN_WIDTH;
  }

  function onPointerDown(event) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { startWidth: width };
    setDragging(true);
    document.body.classList.add("chat-resizing");
  }

  function onPointerMove(event) {
    if (!drag.current) return;
    const wanted = window.innerWidth - event.clientX;
    if (wanted >= MIN_WIDTH) {
      setWidth(Math.min(wanted, maxWidth()));
      setOffset(0);
    } else {
      setWidth(MIN_WIDTH);
      setOffset(MIN_WIDTH - wanted);
    }
  }

  function finishDrag() {
    if (!drag.current) return;
    const { startWidth } = drag.current;
    drag.current = null;
    setDragging(false);
    document.body.classList.remove("chat-resizing");
    if (offset > DISMISS_PAST) {
      // Pushed out: close from where it is, and open next time at the width it had before.
      restore.current = startWidth;
      onDismiss();
    } else {
      setOffset(0);
      saveWidth(width);
    }
  }

  /** Before opening again: back in place, at the width it had before it was pushed out. */
  function settle() {
    setOffset(0);
    if (restore.current !== undefined) {
      setWidth(restore.current);
      restore.current = undefined;
    }
  }

  function resizeBy(change) {
    const next = clamp(currentWidth() + change);
    setWidth(next);
    saveWidth(next);
  }

  function reset() {
    setWidth(null);
    saveWidth(null);
  }

  const percent = width ? Math.round((width / window.innerWidth) * 100) : 50;

  return {
    dragging,
    settle,
    style: {
      width: width ? `${width}px` : undefined,
      transform: offset ? `translateX(${offset}px)` : undefined,
      "--chat-from": `${offset}px`, // where the slide-out starts
    },
    handleProps: {
      role: "separator",
      "aria-orientation": "vertical",
      "aria-label": "Resize chat panel",
      "aria-valuemin": 0,
      "aria-valuemax": 100,
      "aria-valuenow": percent,
      "aria-valuetext": `${percent}% of the window`,
      title: "Drag to resize · double-click for half the window",
      tabIndex: 0,
      onPointerDown,
      onPointerMove,
      onPointerUp: finishDrag,
      onPointerCancel: finishDrag,
      onLostPointerCapture: finishDrag,
      onDoubleClick: reset,
      onKeyDown(event) {
        if (event.key === "ArrowLeft") resizeBy(KEY_STEP);
        else if (event.key === "ArrowRight") resizeBy(-KEY_STEP);
        else if (event.key === "Home") reset();
        else return;
        event.preventDefault();
      },
    },
  };
}
