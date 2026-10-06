# Lifecycle overview

R1 runs every implementation through the same ten phases. This page is the readable summary. The machine-readable rules are in [`lifecycle/lifecycle.yaml`](../lifecycle/lifecycle.yaml) and the gate details are in [`lifecycle/gates.yaml`](../lifecycle/gates.yaml); when this page and those files differ, the files win.

1. Initiate
2. Discover
3. Design
4. Build
5. Validate
6. Enable
7. Launch
8. Stabilize
9. Transition
10. Review

## How moves work

- A project moves forward one phase at a time. Skipping a phase is illegal.
- A forward move needs the current phase's gate outcome to be `pass` or `pass_with_conditions`, recorded by a named human. A `hold` keeps the project where it is.
- The only backward move is Validate to Build, for rework. The project gets a new Build phase instance, so the first attempt stays in the history.
- Review is the last phase. Nothing follows it.

## The phases

| # | Phase | Purpose | Typical operational question | Minimum expected evidence | Legal next phase | Gate |
|---|---|---|---|---|---|---|
| 1 | Initiate | Confirm the commitment, scope, team, and target dates | "Do we agree what we are doing, by when, and who owns it?" | Scope summary, project plan with milestones and tasks | Discover | Yes, `initiate_gate` |
| 2 | Discover | Learn the current state, goals, constraints, and requirements | "Do we understand how they work today and what must change?" | Current-state summary, prioritized requirements list | Design | Yes, `discover_gate` |
| 3 | Design | Agree how the system and ways of working will meet the requirements | "Has the customer approved a design that covers the high-priority requirements?" | Solution design, recorded design approval | Build | Yes, `design_gate` |
| 4 | Build | Configure the system and integrations to the approved design | "Is the build complete and does every integration work end to end?" | Integration test record (configuration record unless a profile waives it) | Validate | Yes, `build_gate` |
| 5 | Validate | Test the build with the customer and iterate until it is accepted | "Has the customer accepted the build, with no open sev1 or sev2 issue?" | Acceptance results, acceptance sign-off | Enable, or Build for rework | Yes, `validate_gate` |
| 6 | Enable | Prepare the people who will use and support the system | "Is every user group trained and is support ready?" | Training completion records, support runbook | Launch | Yes, `enable_gate` |
| 7 | Launch | Review readiness, record the launch decision, and put the system into use | "Given the readiness scorecard and checks, does a named person decide to launch?" | Readiness scorecard, launch plan | Stabilize | Yes, `launch_gate` (the launch decision) |
| 8 | Stabilize | Support early use and resolve launch issues | "Is early use stable enough to hand over?" | Stabilization summary | Transition | Yes, `stabilize_gate` |
| 9 | Transition | Hand ongoing ownership to the long-term team | "Has the support owner accepted ownership, and does every open item have an owner?" | Accepted handoff record, open items list | Review | Yes, `transition_gate` |
| 10 | Review | Capture lessons and signal improvements to the method | "What should change in how we deliver next time?" | Lessons learned, improvement signals | None (last phase) | No gate; Review closes the project |

## What every phase shares

- **Owner roles, not people.** Each phase names owner roles. One person may hold several roles.
- **Events.** Entering and leaving a phase emit `phase.entered` and `phase.exited`. Gates emit `gate.assessed`. Each phase lists its events in `lifecycle.yaml`.
- **Stage behavior.** Every phase has the same purpose at every organization stage. Only the formality of its evidence changes, from lightweight (startup) to formal (structured growth and mature). See [scaling-model.md](scaling-model.md).

## Mapping your own phase names

Organizations often use their own phase names. Map each local name to one of the ten phases instead of adding a phase. For example, a local "kickoff" step belongs to Initiate, and a local "user acceptance testing" step belongs to Validate. If a local process has no equivalent of a phase, the phase still exists and passes through quickly with lightweight evidence.
