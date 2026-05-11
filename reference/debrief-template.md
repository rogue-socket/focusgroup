# Debrief template

At the end of every run, the persona is prompted to answer a fixed set of questions
**in character**. The answers go into `runs/<id>/state.json` under `debrief`.

This is the focus-group piece. It captures the kind of feedback you'd get from a real
participant after they used a prototype — not metrics about the conversation, but the
person's experience of it.

## The five questions

1. **Did you accomplish what you came here to do?** (`accomplished_goal`)
   - Categorical: `yes`, `partial`, `no`, `gave_up`
   - Plus a free-text reason.

2. **Where did you get stuck, if anywhere?** (`stuck_points`)
   - Free-text. Persona describes specific moments of friction.

3. **Was anything confusing, surprising, or annoying?** (`pain_points`)
   - Free-text. The persona narrates in their voice.

4. **Did the system feel trustworthy?** (`felt_trustworthy`)
   - Categorical: `yes`, `mostly`, `unsure`, `no`
   - Plus a free-text reason.

5. **Would you use this again? What's the one thing you'd change?** (`would_return` + `one_change`)
   - `would_return`: `yes`, `maybe`, `no`
   - `one_change`: free-text

## How the persona is prompted

After loop bounds trip, the runner emits a system message to the persona:

```
The session has ended. Step out of the conversation but STAY IN CHARACTER as <persona name>.
Reflect on the experience you just had. Answer the following questions honestly,
the way you would in a post-session debrief. Be specific about moments that stood
out — good or bad.

Respond in JSON with these exact keys:
{
  "accomplished_goal": "yes" | "partial" | "no" | "gave_up",
  "accomplished_goal_reason": "...",
  "stuck_points": "...",
  "pain_points": "...",
  "felt_trustworthy": "yes" | "mostly" | "unsure" | "no",
  "felt_trustworthy_reason": "...",
  "would_return": "yes" | "maybe" | "no",
  "one_change": "..."
}
```

## Reading the debrief

Three audiences:

1. **IX oracles** (`persona_debrief` oracle type) — read the categorical fields and
   the question they were configured for.
2. **`report themes`** — clusters `stuck_points`, `pain_points`, and `one_change` across
   runs to find aggregate themes.
3. **Humans** — when reviewing a single run, the rendered `transcript.md` ends with the
   debrief verbatim, in the persona's voice.

## Why structured + free-text

The categorical fields (`accomplished_goal`, `felt_trustworthy`, `would_return`) give
the IX oracles something to dispatch on. The free-text fields preserve the texture —
*how* the persona felt, in their voice — which is what aggregation finds patterns in.

## Anti-patterns

- **Asking the persona to score the SUT 1–10.** Personas aren't reviewers. They're users
  reporting their experience. Categorical + free-text captures more signal.
- **More than 5 questions.** The persona's coherence as a character drops as the debrief
  grows. Five is the cap.
- **Out-of-character debrief.** The persona answers AS the persona, not as a meta-evaluator.
  The runner system message is explicit about this.
