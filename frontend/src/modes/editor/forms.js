/** A number box's text as a number, or `null` when the box is empty. */
export const toNumber = (text) => (text === "" ? null : Number(text));
