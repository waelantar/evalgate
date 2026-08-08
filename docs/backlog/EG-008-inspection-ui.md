# EG-008: Accessible answer and evidence inspection UI

- Status: Planned
- Branch: `feat/eg-008-inspection-ui`
- Depends on: EG-007 merged to `main`
- Release: R2
- Blueprint requirements: G-03, FR-04, FR-05, NFR-06

## Outcome

A keyboard user can ask, observe an ordered stream, cancel it, distinguish every state, and inspect only server-validated citations and retrieved evidence.

## Scope

- Typed API client and reducer/state machine for idle, submitting, retrieving, streaming, completed, failed, and cancelled states.
- Bounded question form, cancel control, evidence list, citation-to-source navigation, version metadata, empty/unanswerable/error views.
- Safe text/Markdown presentation with raw HTML off and safe link schemes.
- Responsive design tokens/CSS and initial automated accessibility tests.

## Non-goals

- Accounts, chat history, analytics, global state framework, Tailwind, WebSocket, evaluation results, or activation of model-written unvalidated citations.

## Acceptance evidence

- [ ] Component tests cover every state, duplicate/out-of-order rejection, cancellation, provider error, empty evidence, and unanswerable result.
- [ ] Playwright happy/cancel/error/citation flows pass against controlled adapters.
- [ ] Keyboard/focus/live-region/accessible-name/axe checks pass; reduced motion is honored.
- [ ] Citation links activate only after `citations.completed` and use server-derived metadata.

## Required tests and review

- Run reducer/state, component, stream-failure, cancellation, safe-rendering, keyboard, axe, and Playwright happy/error/citation flows; review focus, announcements, responsive behavior, and citation activation.

## Expected file ownership

- Web API types/client, stream reducer/state machine, ask/evidence UI components, constrained rendering utilities, CSS/design tokens, component tests, and Playwright fixtures/specs.

## Stop conditions

- A new UI/state/design framework, content persistence, authentication, or stream-contract change is needed.

## Copy-paste coding-agent brief

> Work only on EG-008 on branch `feat/eg-008-inspection-ui`. Read `AGENTS.md`, `BLUEPRINT.md`, ADR-0005, the frozen stream/search contracts, and this story. Confirm EG-007 is merged to clean `main`. Build the accessible state-driven ask/stream/cancel/evidence UI using the existing parser, safe rendering, server-validated citations, and complete component/E2E state tests. Do not add accounts, history, analytics, new UI/state frameworks, or evaluation screens. Do not merge, push, deploy, or start EG-009. Finish with state/data-flow and accessibility explanation, changed files, exact evidence, limitations, and suggested commit message.
