/**
 * The editor's "Load JSON..." button. It opens the browser's file picker through a hidden
 * file input and passes the input's change event to `onLoad` (eventHandlers' loadFile).
 */
import { useRef } from "react";
import Button from "../../components/Button.jsx";

export default function LoadJsonButton({ onLoad }) {
  const inputRef = useRef(null);
  return (
    <>
      <Button onClick={() => inputRef.current.click()}>Load JSON...</Button>
      <input ref={inputRef} type="file" style={{ display: "none" }} onChange={onLoad} />
    </>
  );
}
