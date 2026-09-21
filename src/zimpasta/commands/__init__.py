"""Command modules, one per feature.

Each module exposes a ``SPECS`` tuple of ``zimpasta.command.CommandSpec``. A spec pairs
the command's grammar with two functions:

* ``handler(console, session, invocation)`` does the work for a complete command and
  never prompts for arguments (it may still ask a yes/no confirmation);
* ``builder(console, session, invocation)`` prompts for whatever required values are
  missing and returns the completed invocation, or ``None`` if the user cancels.

The evaluator in ``zimpasta.command`` runs both paths, so ``add`` alone and
``add course "CS 101" ...`` end up in the same handler. Talk to the user only through the
``Console``, keep session state on the ``Session``, and use ``zimpasta.prompts`` so invalid
input re-prompts instead of raising.
"""
