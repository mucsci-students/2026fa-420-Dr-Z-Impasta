/**
 * Where Dr. ZImpasta's answers come from.
 *
 * For now this is a placeholder, so the chat panel can be built and tried before the
 * chatbot exists: it waits a moment and says it isn't connected yet.
 *
 * To connect a real chatbot, replace the body with a call to it (for example a new route
 * in the Python API, src/zimpasta/controller/routes.py, called through api/client.js) and
 * return the reply's text. Throw an Error to show a failed answer in the chat.
 *
 * @param {{ role: "user" | "assistant", text: string }[]} messages the conversation so far,
 *   oldest first; the last one is the question to answer.
 * @returns {Promise<string>} the reply
 */
export async function askDrZimpasta(messages) {
  const question = messages.at(-1)?.text ?? "";
  await new Promise((resolve) => setTimeout(resolve, 700));
  return (
    `You asked: “${question}”\n\n` +
    "I'm not connected to a chatbot yet, so I can't answer questions. " +
    "This is the chat window; answers will show up here once it is."
  );
}
