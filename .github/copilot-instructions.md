# Repository Instructions (TDD First)

These instructions apply to all coding tasks in this repository.

## Core Rule

- Use TDD by default: Red -> Green -> Refactor.
- Do not write or change production code before adding a failing test that proves the target behavior.

## Required Workflow

1. Define expected behavior first.
2. Add or update a test that fails for the right reason.
3. Implement the minimum production change to make the test pass.
4. Refactor safely while keeping tests green.
5. Run relevant tests before finishing.

## Testing Expectations

- Prefer small, focused tests close to the changed behavior.
- Add regression tests for bug fixes.
- If there is no existing test file, create one using the project's current test style.
- For Python code, prefer `pytest` style tests unless the target area already uses another framework.

## Delivery Expectations

- In change summaries, explicitly report:
  - what test was added/updated first,
  - what implementation was changed after the failing test,
  - which tests were run and their result.

## Exception Policy

- If a task cannot reasonably follow TDD (for example, one-off scripts or purely mechanical edits), state why and still add validation checks when possible.

## Additional Coding Constraints (andrej-karpathy-skills style)

Apply the following behavior by default in all coding tasks:

- Think before coding:
  - State key assumptions explicitly.
  - If requirements are ambiguous, ask or present options before implementation.
  - Call out simpler alternatives when they exist.

- Simplicity first:
  - Implement only what is requested.
  - Avoid speculative abstractions, configurability, or future-proofing not required by the task.
  - Prefer the smallest change that solves the stated problem.

- Surgical changes:
  - Touch only lines directly related to the request.
  - Do not refactor or reformat unrelated code.
  - Remove only dead code introduced by the current change; do not clean pre-existing unrelated code unless asked.

- Goal-driven execution:
  - Define clear success criteria before implementation.
  - For multi-step tasks, keep a short plan and verify each step.
  - For bug fixes, prefer reproducing the bug in a test before changing implementation.