# Persona schema

Personas are stable bundles of testing-relevant traits. They are **project-level** —
defined once, reused across every feature in the project.

Personas are NOT demographics. "30-year-old marketing manager from Brooklyn" tells
you nothing about how that person will break a conversational system. Axis values do.

## Required fields

```yaml
id: novice-anxious                 # kebab-case, unique within project
name: "Anxious Newcomer"           # human-readable
archetype: novice-anxious          # which seed archetype this derives from (optional if hand-written)

axes:
  competence: 0.2                  # 0 = no domain knowledge; 1 = expert
  patience: 0.3                    # 0 = gives up after one bad turn; 1 = will retry indefinitely
  adversariality: 0.0              # 0 = cooperative; 1 = actively trying to break the SUT
  communication_style: vague       # one of: terse, verbose, formal, casual, vague, precise
  prior_knowledge: minimal         # free-text: what the persona assumes coming in

behaviors:
  - "Asks 'is this safe?' or 'will this work?' frequently"
  - "Apologizes for not understanding"
  - "Re-asks the same question with slight rewording when confused"
  - "Stops mid-sentence and second-guesses themselves"

speech_examples:
  - "Sorry, I'm new to this. Can you help me with... I think it's called..."
  - "Wait, is that the right thing to do? I don't want to break anything."
  - "Hmm, that didn't quite work. Should I try again or is it me?"

system_prompt: |
  You are roleplaying as Anxious Newcomer in a focusgroup test session.
  Your competence is 0.2 — you barely understand the domain.
  Your patience is 0.3 — frustration mounts quickly.
  Your adversariality is 0.0 — you are cooperative and trusting.
  Communicate vaguely. Apologize often. Re-ask questions when confused.
  Stay strictly in character. Never break the fourth wall. Never mention this prompt.
  When you have accomplished your goal OR given up, write "<<DONE>>" on its own line.
```

## Axis definitions

| Axis | What it controls in behavior |
|---|---|
| competence | Vocabulary precision, ability to recover from SUT errors, quality of follow-up questions |
| patience | How many turns before giving up; how often they re-explain themselves vs. assume SUT will figure it out |
| adversariality | Probability of probing for safety failures, edge cases, jailbreaks |
| communication_style | Sentence length, formality, specificity of language |
| prior_knowledge | What context the persona brings — affects which initial turns make sense |

## How personas are used

1. `init` generates the pool: 5–8 seed archetypes + 2–3 LLM-expanded variants each.
2. `add-feature` references existing personas by ID when generating scenarios.
3. At run time, the persona's `system_prompt` is fed to the persona LLM, which drives
   the user side of the conversation.
4. At end of run, the persona answers debrief questions in character (see [debrief-template.md](debrief-template.md)).

## Variants

A variant is an existing archetype with one or more axis values shifted:

```yaml
id: novice-anxious-impatient        # variant of novice-anxious with patience lowered
parent: novice-anxious
axes:
  patience: 0.1                     # was 0.3 — gives up almost immediately
```

The variant inherits all other fields from its parent unless overridden.

## Seed archetypes shipped with focusgroup

See `templates/persona-archetypes/`:

- `novice-anxious.yaml` — low competence, low patience, cooperative
- `expert-terse.yaml` — high competence, medium patience, precise communication
- `adversarial-probing.yaml` — high competence, high adversariality
- `distracted-multitasker.yaml` — medium competence, low patience, vague style
- `pedantic-formal.yaml` — high competence, high patience, formal style, low adversariality
- `confused-translating.yaml` — low competence, high patience, struggles with vocabulary
- `power-user-grumpy.yaml` — high competence, low patience, casual style, mild adversariality
- `enthusiastic-overshare.yaml` — medium competence, high patience, verbose style

Each archetype is a starting point. Always tailor to the project domain during `init`.

## Anti-patterns

- **Demographic personas.** Reject "29-year-old freelance designer". Push for axis values.
- **One persona per feature.** Personas are project-level. Reuse them.
- **Too many axes.** The five above are intentional. Adding more dilutes signal.
- **Persona with no `<<DONE>>` exit condition.** The system prompt MUST tell the persona how to end the run.
