# Principles

## Core Principles

- Alignment over raw output
- Validation over optimistic completion
- Explicit responsibility over blurred ownership
- Escalation over false confidence
- Controlled iteration over endless refinement
- Existing coding agents are components, not the product

## Non-Negotiable Rules

### No self-approval

The role that produces work cannot be the role that approves it. Developers cannot approve their own output. Architects cannot bypass validation. Product cannot redefine completion after the fact to force approval.

### AVA is blocking

Nothing is done without AVA approval. Rejection is not advisory. It must send the task back for rework or escalation.

### Integration is explicit

System-level integration must be checked explicitly. Implementation quality alone is not enough.

### Iteration has limits

Retries must be capped and controlled. If a task cannot converge within the limit, the system must escalate rather than loop indefinitely.

### Termination must be defined

Every task must have clear success criteria and a clear completion signal. Otherwise the system will drift or refine forever.

## Autonomy Boundary

Minimal human intervention does not mean zero human involvement.

Humans are still responsible for:

- defining goals and constraints
- setting policy boundaries
- resolving ambiguity when the system cannot infer intent safely
- making exceptional judgment calls when escalation is required

Everything else should be automated by default.

## Failure Modes To Design Against

### Looks done

The system produces output that appears complete but does not satisfy the actual requirement.

### Spec drift

The implementation becomes technically coherent but moves away from the original user intent.

### Integration illusion

Individual steps look correct, but the full system behavior has not been validated.

### Infinite refinement

Agents continue revising, debating, or polishing without a clear completion condition.

### Multi-agent theater

The system creates many roles and messages without gaining real control, traceability, or decision quality.

## Principle For Evaluation

The system should be judged by whether it reduces coordination burden while preserving trust, not by how many agents it can run at once.
