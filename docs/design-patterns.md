Dr. ZImpasta — Design Pattern Reference
This document identifies seven distinct design patterns used in Dr. ZImpasta and directs reviewers to the relevant application code. Each entry explains the problem addressed, code location, participants, interaction, and fit with the pattern. The existing implementation descriptions are drawn from the team's README and architecture documentation; source and test references should be checked against the final submitted branch.
At-a-glance index
#	Pattern	Primary implementation	What it solves
1	Model–View–Controller (MVC)	src/zimpasta/model/; src/zimpasta/controller/app_controller.py; frontend/src/	Separates scheduling rules, application workflows, and UI
2	Command	src/zimpasta/command.py; src/zimpasta/commands/; src/zimpasta/controller/assistant/tools.py	Runs many distinct user actions through consistent invocation paths
3	Strategy	src/zimpasta/model/generation_job.py	Runs the scheduler using threads or an async event loop without changing the job
4	Adapter	src/zimpasta/controller/assistant/client.py	Shields the application from the OpenAI SDK's interface
5	Memento	frontend/src/state/configEditorMemento.js; frontend/src/state/eventHandlers.js	Supports undo and redo of configuration edits
6	Observer	src/zimpasta/model/observable.py; src/zimpasta/model/workspace.py; src/zimpasta/model/schedules.py; src/zimpasta/model/accounts/service.py	Notifies account-state persistence when application state changes
7	Repository	src/zimpasta/model/accounts/records.py; src/zimpasta/model/accounts/sql_store.py	Separates account logic from SQLite/Neon data access


Naming note: “Class patterns” in scheduling configuration are a domain concept, not one of the software design patterns listed here.

1. Model–View–Controller (MVC)
Problem. Scheduling rules must stay consistent across the React GUI, command-line shell, and AI assistant. User-interface code should not duplicate configuration validation or schedule-generation rules.

Files / participants.
- Model: src/zimpasta/model/ — particularly ConfigWorkspace, GenerationJob, and ScheduleSet; owns configuration state, solver execution, and generated schedules.
- Controller: src/zimpasta/controller/app_controller.py (AppController) and web API routes; coordinates application workflows.
- View: frontend/src/ and frontend/src/api/client.js; collects user input and displays results.
Interaction. A GUI action calls api.*, which reaches an API route and an AppController method. The controller invokes model operations and returns data for the view to display. The shell and assistant use the same underlying application rules.

Why it fits. Model logic is kept separate from HTTP/rendering; controllers orchestrate workflows; views do not validate scheduler rules themselves.

Reviewer starting points: README.md → “Architecture (MVC)”; docs/gui.md.
2. Command
Problem. The shell and AI assistant support many distinct actions, each requiring argument processing and a predictable execution/result path.

Files / participants.
- Command descriptors: CommandSpec in src/zimpasta/command.py; Tool in src/zimpasta/controller/assistant/tools.py.
- Concrete commands: command modules under src/zimpasta/commands/ and the assistant's registered tools.
- Invokers: evaluate() / Registry for the shell; ToolRegistry.dispatch() for the assistant.
- Receivers: Session, the Model, and AppController.
Interaction. The caller provides an action name and arguments. The invoker resolves and validates a command, executes the associated handler, and reports the result without embedding the behavior of every action in the caller.

Why it fits. Actions are encapsulated as independently registered specifications/tools with a common invocation mechanism. New actions can be registered without rewriting the main shell or chat dispatch loop.

Reviewer starting points: src/zimpasta/command.py; src/zimpasta/controller/assistant/tools.py; tests/test_command.py; tests/controller/assistant/test_tools.py.
3. Strategy
Problem. Schedule generation must remain responsive in two execution environments: a server that can use threads and a browser/Pyodide environment that uses an event loop.

Files / participants.
- Context: GenerationJob in src/zimpasta/model/generation_job.py.
- Strategy contract: a runner implementing start(work) and wait(timeout).
- Concrete strategies: ThreadRunner and EventLoopRunner.
- Selection: AppController accepts a runner; the browser application supplies EventLoopRunner, while the server normally uses ThreadRunner.
Interaction. GenerationJob produces schedule-generation work and delegates its execution to the selected runner; generation status and cancellation remain the job's responsibility.

Why it fits. Execution algorithms are interchangeable behind the same runner contract, keeping platform-specific scheduling mechanics outside the job's core behavior.

Reviewer starting points: src/zimpasta/model/generation_job.py; src/zimpasta/browser.py; tests/model/test_generation_job.py.
4. Adapter
Problem. The AI assistant needs a stable interface independent of the OpenAI SDK's request fields, response objects, and exceptions, including for tests that do not contact a remote API.

Files / participants.
- Target interface: AIClient protocol in src/zimpasta/controller/assistant/client.py.
- Adaptee: OpenAI SDK Responses API.
- Adapter: OpenAIClient in the same file.
- Client: Assistant in src/zimpasta/controller/assistant/session.py.
Interaction. The assistant calls AIClient.respond(...); OpenAIClient converts the request into SDK options, translates SDK responses into AIReply / ToolCall, and maps SDK failures into application-level AIError messages. Tests can substitute a fake implementing the same protocol.

Why it fits. It explicitly translates an external service interface into an application-owned interface, reducing coupling to SDK-specific types.

Reviewer starting points: src/zimpasta/controller/assistant/client.py; tests/controller/assistant/test_openai_client.py; tests/controller/assistant/test_session.py.
5. Memento
Problem. Users editing configurations need undo and redo without manually reconstructing earlier values.

Files / participants.
- frontend/src/state/configEditorMemento.js — configuration-editor history/snapshot support.
- frontend/src/state/eventHandlers.js — editor actions that route changes through history handling.
Interaction. The editor saves restorable states as edits occur. Undo and redo navigate previously captured states and restore the relevant configuration state through the editor's application flow.

Why it fits. Earlier states are captured and later restored to reverse user actions, instead of requiring an inverse operation for every edit.

Reviewer starting points: the two files above; README.md → “Memento”. Confirm the exact function names and snapshot/restoration flow on the final branch.
6. Observer
Problem. Account-state saving must respond to configuration and schedule changes regardless of which UI or application action caused them; individual editing methods should not need to know about account persistence.

Files / participants.
- Change notification machinery: src/zimpasta/model/observable.py.
- Subjects / publishers: src/zimpasta/model/workspace.py and src/zimpasta/model/schedules.py.
- Subscriber / listener: src/zimpasta/model/accounts/service.py, which handles saved application state.
Interaction. When a workspace or schedule-set change occurs, the model emits a change notification. The account-state service can respond to these notifications and save the current state without the modifying code directly calling account storage.

Why it fits. Change producers are decoupled from a dependent reaction through a notification mechanism. This is an application-owned Observer design, not merely React's built-in reactivity.

Reviewer starting points: files above; README.md → “Added in Sprint 4” / “Observer”. Confirm registration, notification and listener method names in the final branch.
7. Repository
Problem. Account and saved-state operations should not require business logic to know whether records are stored in the production Neon database or the SQLite test database.

Files / participants.
- Repository abstraction / record contracts: src/zimpasta/model/accounts/records.py.
- SQL-backed repository implementation: src/zimpasta/model/accounts/sql_store.py.
- Client: account service code in src/zimpasta/model/accounts/service.py.
- Storage backends: Neon (production) and SQLite (tests), as described in the project's existing README.
Interaction. Account service code performs user/saved-state operations via a data-access abstraction. The SQL implementation translates these operations into persistent storage actions; tests can use SQLite without rewriting application logic.

Why it fits. Persistence details are isolated behind a repository interface, separating account behavior from database-specific access.

Reviewer starting points: files above; docs/accounts.md; README.md → “Repository”. Confirm concrete interface names and supported operations in the final branch.
Evidence and verification
The pattern inventory is documented in the team's README history (fa9ceb8, ca71110). The Memento, Observer, and Repository summaries above are based on the documented file map and feature descriptions; verify the exact methods in the current submission branch. The other entries also should be checked against the version actually submitted.

Suggested final check from the repository root:
for file in \
  src/zimpasta/model/generation_job.py \
  src/zimpasta/controller/assistant/client.py \
  frontend/src/state/configEditorMemento.js \
  frontend/src/state/eventHandlers.js \
  src/zimpasta/model/observable.py \
  src/zimpasta/model/accounts/records.py \
  src/zimpasta/model/accounts/sql_store.py; do
  test -f "$file" && echo "OK: $file" || echo "MISSING: $file"
done
uv run pytest
Documentation is evidence of design intent, but grading also depends on the listed code being