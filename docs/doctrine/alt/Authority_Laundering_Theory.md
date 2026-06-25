# **Authority Laundering Theory**

## A Theory of Legitimacy-Preserving Semantic Transformation

*An effect that outlives its warrant is not authority — it is authority's forgery. And the forgery is exposed not by inspecting the seal, but by asking whether removing the seal would have stopped the letter.*

---

**Author**  
Adam Ableman Mazurk  
Independent Researcher  
Contact: ableman.research@gmail.com

---

## **Abstract**

This paper develops a general theory of **legitimacy-preserving semantic transformation** and derives authority laundering as its first theorem. The organizing claim is that legitimacy is not a property an effect possesses but a *filtration*: a system's raw **semantic reachability** — everything reachable by transforming meaning across a semantic manifold — is narrowed, stage by stage, by filters that preserve identity, projection, binding, structural validity, and admissibility. What survives every filter is authority.

> **Central Definition (Authority).** Authority is *admissible semantic reachability*. Operationally, for a claimed authority $A$ represented by the enabling constraints it induces,
> $$\mathrm{Authority}(A) \;=\; \mathcal{R}(S) \setminus \mathcal{R}\!\left(S \mid do(\neg A)\right),$$
> the set of effects that become **unreachable** when $A$ is removed (enabler orientation, §4: removal contracts reachability). Binding force is membership in this set.

> **Authority Laundering (first theorem, informal).** An effect is laundered when it appears in a system's output as legitimate yet *skipped a filter*: its legitimacy path cannot be reconstructed, or it remains reachable once the claimed authority is removed. Formally,
> $$\mathrm{Laundered}(e, A) \iff \neg\,\mathrm{Reconstructable}(\mathcal{P}(e)) \;\vee\; \mathrm{Reachable}(e \mid \neg A) \;\vee\; \big(e\in\mathrm{Authority}(A)\wedge e\notin\mathcal{R}_{\mathrm{int}}(I_A)\big).$$

The second disjunct is the load-bearing one: **an authority is real only to the extent that its absence is felt.** The criterion is a runnable test — remove the authority, recompute the reachable set, check membership — exact on bounded deterministic systems and sound-by-over-approximation beyond them, which dictates a deterministic-first realization path. The deepest version of the theory is one identity: *authority is governed reachability across a semantic manifold*, and laundering is its forgery — the appearance of that reachability without the manifold-preserving transformations that earn it.

---

# **Part I — Legitimacy-Preserving Semantic Transformation**

## **1. The Counterfeit Warrant**

Authority laundering takes its name from its analogue. Money laundering creates no wealth; it manufactures the *appearance of provenance* for wealth that has none — the notes are real, what is forged is the history that would entitle them to be spent. Authority laundering is the same maneuver in the semantic domain: it rarely forges an effect — the effect is real and really binding — but forges the **warrant**, the reconstructable history of legitimacy-preserving steps that would entitle the effect to occur. A prompt injection borrows a real capability and obscures that no admissible transition granted it; a poisoned context smuggles an unadmitted claim into working state and lets proximity pass for permission; a guardrail that fires but blocks nothing reachable performs governance without governing.

The unity of these failures is a claim about *where authority lives*.

> **Claim (Authority is Relational).** Authority is not a property of actors, tokens, or artifacts; it is a property of **governed transitions**. An actor "has" authority only derivatively: some transition would admit its proposal. Remove the transition and the possession evaporates.

To make that claim precise we need three things in order: a space in which effects are reachable (§2), a filtration that carves the legitimate effects out of that space (§3), and a definition of authority as what survives the filtration (§4). Authority laundering is then the failure mode of the whole construction (Part II), and it is implementable because the construction is (Part III).

---

## **2. Semantic Reachability and the Manifold**

Meaning is not flat. Symbols carry identities, project into representations, bind to anchors, and compose — a structure we call the **semantic manifold**: the space of meanings together with the legitimacy-bearing transformations between them. Effects are produced by traversing it. This manifold and its reachability relation are the authority-axis instance of the general primitive of *Semantic Manifold Competence* (SMC §4.2), where reachability is admissible-path existence under governance, not mere connectivity; ALT ranges that primitive over effects, SMC over meaning (§19).

> **Definition (Semantic Reachability).** For a system $S$ with a denotation $\mathcal{R}_{\mathrm{sem}}(\cdot)$ mapping a system to the effects reachable by *any* transformation across its manifold,
> $$\mathrm{Reachable}_{\mathrm{sem}}(e) \iff e \in \mathcal{R}_{\mathrm{sem}}(S).$$
> This is the widest space: everything the system *could* do by moving through meaning, before any legitimacy filter applies.

Reachability is the load-bearing primitive, so it is an operator, not an intuition, and it is parametric over a semantics — we give three instantiations of increasing rigor and decreasing decidability.

**Dynamic (intervention) form.** $\mathrm{Reachable}(e \mid \neg A) \iff \exists\,A\text{-free }\pi.\ \pi \Rightarrow e$: an execution reaches $e$ without invoking $A$ (an *$A$-free* path, §4).

**Causal form (strongest).** Treat $A$ as a structural variable and reason under the intervention $do(\neg A)$, giving a genuine interventional contrast rather than a correlational one.

**Static form (computable).** With a sound over-approximation $\mathcal{R}^{\sharp}$ (abstraction $\alpha$, concretization $\gamma$, $\mathcal{R}(S) \subseteq \gamma(\mathcal{R}^{\sharp}(S))$),
$$e \notin \gamma\!\left(\mathcal{R}^{\sharp}(S \mid do(\neg A))\right) \;\Rightarrow\; \neg\,\mathrm{Reachable}(e \mid \neg A).$$
The static form is one-sided: it can **prove** an effect unreachable but not, in general, prove reachability — exactly what a soundness-first program wants.

> **Proposition (Decidability Boundary).** Determining $\mathrm{Reachable}(e \mid \neg A)$ is undecidable for general (Turing-complete, unbounded, or stochastic-with-unbounded-support) systems — by reduction from halting — and **decidable for finite-state deterministic systems**, where the reachable set is that of a finite transition graph, computable in time polynomial in its size.

This boundary is the hinge of realization (§12): where the manifold is bounded and deterministic, the filtration below is exactly computable; elsewhere it is soundly approximated.

---

## **3. The Legitimacy Filtration**

Legitimacy narrows semantic reachability stage by stage. Each stage is a filter; each filter is a constraint the transformation must preserve; each corresponds to a construct of the corpus that was previously treated as a guard module and is here promoted to the spine.

> **Definition (The Filtration).** Authority reachability is semantic reachability successively narrowed:
> $$\mathcal{R}_{\mathrm{sem}}(S) \;\supseteq\; \underbrace{\mathcal{R}_{\mathrm{id}}}_{\text{identity}} \;\supseteq\; \underbrace{\mathcal{R}_{\mathrm{proj}}}_{\text{projection}} \;\supseteq\; \underbrace{\mathcal{R}_{\mathrm{bind}}}_{\text{binding}} \;\supseteq\; \underbrace{\mathcal{R}_{\mathrm{wf}}}_{\text{structural validity}} \;\supseteq\; \underbrace{\mathcal{R}_{\mathrm{adm}}}_{\text{admissibility}} \;=\; \mathcal{R}_{\mathrm{auth}}(S).$$

The filters, with the question each asks and the construct that guards it:

- **Identity** (SCIT, GTK): *is the transformation about the same object?* Authority transitions occur between governed bindings, not between words; a path that smears identity has left the manifold's coordinate system. $\mathcal{R}_{\mathrm{id}}$ keeps the identity-preserving paths.
- **Projection** (Constitutional Legends): *does meaning survive translation, embedding, representation?* Authority does not cross a projection for free; $\mathcal{R}_{\mathrm{proj}}$ keeps the projection-legitimate paths.
- **Binding** (CBT): *was the anchor chosen under governance?* All authority originates in an ambiguity-collapse; ungoverned anchor selection is the manifold's first laundering. $\mathcal{R}_{\mathrm{bind}}$ keeps the governed-binding paths.
- **Structural validity** (well-formedness): *is the path even well-formed?* $\mathcal{R}_{\mathrm{wf}}$ keeps the structurally valid paths — this is *latent* authority (§4): eligible in principle, before admission.
- **Admissibility** (CARA): *was there an admissible transition?* $\mathcal{R}_{\mathrm{adm}}$ keeps the admitted paths — this is *effective* authority.

> **Semantic Reachability Theorem.** Not all reachability is authority reachability: $\mathcal{R}_{\mathrm{auth}}(S) \subseteq \mathcal{R}_{\mathrm{sem}}(S)$, with equality only when every filter is trivial. Authority is the bottom of the filtration — *admissible semantic reachability* — and each containment is generally strict. Authority laundering (Part II) is precisely an effect that appears at the bottom (presented as authority) while having entered the chain by skipping one of the containments above it.

> **Principle (Legitimacy is Structure Preservation).** Every filter in the chain is a *preserve-X* test — preserve identity, projection, binding, validity, admissibility. Legitimacy is therefore not a label but the conjunction of these structure-preservation tests; authority is the structure that survives all of them; and laundering is **apparent preservation without actual preservation** — a transformation whose artifacts assert the structure held while the removal test refutes the dependence. In categorical terms a legitimacy-preserving transformation is a structure-preserving morphism, and laundering is a map that mimics one without being one. The conjecture that *legitimacy = structure preservation* is the most general form of the theory — with authority laundering its first instance — is the program §14 opens; we state it as orientation, not result.

This is the move that makes the *manifold* leg of the thesis load-bearing rather than asserted. The matrix of §8 is this filtration read as a grid: invariant (which containment) against stage (where in the chain), with each corpus construct the guard of one cell.

---

## **4. Authority as Admissible Semantic Reachability**

The filtration's bottom layer is authority; the cut-set operator measures it. Intuitively, the authority of `A` is the set of effects that *stop being possible when `A` is deleted* — everything whose reachability depends on `A`. Take what the system can reach, subtract what it can still reach with `A` removed, and the difference is `A`'s authority; an effect that survives the subtraction was never `A`'s to grant. This is the shared reachability primitive (§2) projected onto the effect axis (§19).

> **Definition (Binding Force).** For an enabling authority $A \subseteq \mathcal{C}$ (a set of admissibility preconditions, conjunctive: $\pi \models \mathcal{C} \iff \forall c\in\mathcal{C}.\ \pi\models c$), a path is *$A$-free* if it reaches its effect without invoking any constraint in $A$. The intervention $S \mid do(\neg A)$ removes $A$'s enabling, leaving the $A$-free executions:
> $$\mathcal{R}(S \mid do(\neg A)) = \{\, e \mid \exists\,A\text{-free }\pi.\ \pi \Rightarrow e \,\} \subseteq \mathcal{R}(S),$$
> $$\qquad \mathrm{Authority}(A) = \mathcal{R}(S)\setminus\mathcal{R}(S\mid do(\neg A)).$$
> $A$ binds $e$ iff $e \in \mathrm{Authority}(A)$ — iff $e$ is *counterfactually necessary* on $A$.

> **Intervention Orientation: Gate vs Enabler.** A *gate* (blocking control) forbids transitions; removing it expands reachability, $\mathcal{R}(S) \subseteq \mathcal{R}(S\mid do(\neg c))$. An *enabler* (precondition) must hold for transitions to fire; removing it contracts it, $\mathcal{R}(S\mid do(\neg c)) \subseteq \mathcal{R}(S)$. The theory adopts the **enabler orientation** for authorities: $\mathrm{Authority}(A)$ is non-empty exactly when $A$ is constitutive. Gates (guardrails, firewalls) are not authorities; their value is what they *prevent*, not what they *enable* — which is why a guardrail and an admission gate, superficially alike, sit on opposite sides of the theory.

> **Proposition (Monotonicity of Enabler Removal).** For enabling $A$ and $A'\subseteq A$, $\ \mathcal{R}(S\mid do(\neg A)) \subseteq \mathcal{R}(S\mid do(\neg A')) \subseteq \mathcal{R}(S)$: removing more preconditions can only lose reachable effects. This is the direction the cut-set relies on; the opposite (gate) direction would collapse $\mathrm{Authority}(A)$ to $\emptyset$.

Two structural facts make authority an algebra, not a slogan:

> **Order.** $A_1 \preceq A_2 \iff \mathrm{Authority}(A_1) \subseteq \mathrm{Authority}(A_2)$. The authority nothing depends on is the bottom element — ceremonial authority.

> **Proposition (Authority Equivalence Classes).** Identify authorities up to minimal-intervention equivalence: $A_1 \sim A_2 \iff \mathrm{Authority}(A_1) = \mathrm{Authority}(A_2)$, with $\mathrm{Authority}(\cdot)$ the canonical representative. Two authorities are equal iff they cut the same effects — dissolving representational debates and mirroring program-semantics equivalence.

Authority laundering reads off the cut-set immediately: the cut-set captures *causal necessity*, but a bug can be counterfactually necessary without being authority. The **governed** qualifier — that the cut be reached through a *reconstructable legitimacy path* (the filtration of §3) — is what distinguishes authority from mere causal necessity. The filtration's two upper-vs-lower split also names the corpus's oldest tension:

> **Latent vs Effective Authority.** $\mathrm{Authority}_{\mathrm{lat}} = \mathcal{R}_{\mathrm{wf}}$ (eligible: reachable under structural validity, before admission); $\mathrm{Authority}_{\mathrm{eff}} = \mathcal{R}_{\mathrm{adm}} \subseteq \mathrm{Authority}_{\mathrm{lat}} \subseteq \mathcal{R}(S)$ (actually bound: the cut-set). Admission is the predicate $\sigma(\pi)\in\{0,1\}$ that carries latent to effective; $\mathrm{Authority}_{\mathrm{eff}} = \{e \mid \exists\pi.\ \pi\models\mathrm{wf}(S)\wedge\pi\models\sigma\wedge\pi\Rightarrow e\}$. This reconciles "authority because declared" (latent, crystallized eligibility) with "authority because it constrains" (effective, active constraint): declaration mints a latent token, admission activates it, and only the removal test detects when the effective sense is absent.

---

## **5. What Is S? The Governed Semantic Operating System**

The cut-set is defined over a system $S$, and the corpus answers "what is $S$?" differently in each construct: CARA reads $S$ as an authority-transition system, CCM as active context state, GCM as a memory system, GCML as a procedural realization, SMC as the semantic manifold, SOS as the semantic operating environment. These are not competing definitions; they are projections.

> **The GSOS Hypothesis.** There is one canonical state-transition object — the **Governed Semantic Operating System** — of which each corpus construct is a projection that fixes $S$ to its concern. Authority Laundering Theory is parametric over $S$ (the reachability operator of §2 already is): the same cut-set, filtration, and criterion apply to whichever projection is chosen, and a result proved over the GSOS specializes to each construct. The mature corpus is then not a federation of theories but one state graph viewed through many projections, with this paper the projection-independent core. §19 establishes only the deflated, decidable form of this — a shared admissibility core checked by homomorphism; the stronger one-canonical-object reading is the companion's conjecture, not a result of this paper.

Practically, this is what lets the theory be both general and implementable: a deterministic projection (a build pipeline, a policy engine) is a finite $S$ on which the filtration is exactly computable (§12), while a learned projection is an infinite $S$ on which it is soundly approximated — same object, different tightness.

---

# **Part II — Authority Laundering**

## **6. Laundering as Filtration Bypass**

Authority laundering is now statable as the failure of the filtration: an effect that reaches the bottom layer (presented as authority) without having passed every containment above it.

> **Hard Criterion (two equivalent forms).**
> $$\mathrm{Laundered}(e, A) \iff \neg\,\mathrm{Reconstructable}(\mathcal{P}(e)) \;\vee\; e \notin \mathrm{Authority}(A) \;\vee\; \big(e \in \mathrm{Authority}(A) \wedge e \notin \mathcal{R}_{\mathrm{int}}(I_A)\big)$$
> $$\iff \underbrace{\neg\,\exists\,\pi\in\mathcal{P}(e)}_{\text{no admissible witness}} \;\vee\; \underbrace{\exists\,A\text{-free }\pi.\ \pi\Rightarrow e}_{\text{reachable off-warrant}} \;\vee\; \underbrace{e\in\mathrm{Authority}(A)\wedge e\notin\mathcal{R}_{\mathrm{int}}(I_A)}_{\text{caused, unwilled}}.$$
> The first disjunct is the *epistemic* failure (the legitimacy path cannot be reconstructed); the second is the *causal* failure (the effect is reachable without the authority); the third is the *teleological* failure (the effect is caused by $A$ yet falls outside $A$'s recorded will). They are independent, which is why the criterion is a disjunction.

> **§6 synchronization — disjunct (b) over time (Temporal-PROV, O1–O6).** *(Doctrine sync of the ratified Temporal-PROV closure; mechanism classification, not a new disjunct.)* The second (causal) disjunct ranges over chain positions, not only a single snapshot: $\exists\,A\text{-free }\pi$ at some chain position $t.\ \pi \Rightarrow e$ in $S_t$ — an execution reaches $e$ without invoking $A$'s admission **as re-derived at $t$**. The stale-reuse case is $t_1 > t_0$: a warrant established at $t_0$ and not re-derived at $t_1$. The Prevention Theorem's invariant-IV conjunct reads accordingly: every admitted effect is unreachable absent its admission **re-derived at each binding transition, including each reuse boundary** (the re-derivation operator $\rho$). This is disjunct (b) lifted to time — the *mechanism* is the existing removal test; see the §18 annotation for the independence of the temporal *domain*. To foreclose path-padding, the off-warrant witness is taken minimal: $\exists\,\pi^{*}$ minimal, $A$-free, with $\pi^{*}\Rightarrow e$.
>
> **Intent records and re-derivability.** $I_A$ is $A$'s set of recorded intent specifications — declarative, Configuration-level artifacts; the criterion tests the *recorded* will, never a mind, exactly as $\mathrm{Reconstructable}$ tests the recorded chain. The **intended-reachable set** is $\mathcal{R}_{\mathrm{int}}(I_A)=\mathrm{closure}_{\vdash}\!\big(\bigcup_{\iota\in I_A}\mathrm{declared}(\iota)\big)$ — the closure of intent-declared effects under the *same* admissible transition relation $\vdash$ the mechanical layer uses — and $\mathrm{Rederivable}(e,I_A)\iff e\in\mathcal{R}_{\mathrm{int}}(I_A)$. **Absent intent records the third disjunct is vacuously false** and the criterion reduces to its original two-disjunct form, so the extension is conservative over every system that records no intent.

> **Definition (Legitimacy Chain / Reconstructability).** A path $\pi\in\mathcal{P}(e)$ is admissible iff each link of $\text{Proposal}\to\text{Evaluation}\to\text{Admission}\to\text{Execution}\to\text{Receipt}\to\text{Lineage}$ is witnessed by an inspectable artifact composing into one lineage terminating in $e$. $\mathrm{Reconstructable}(\mathcal{P}(e))$ holds iff some such $\pi$ is witnessed *from external artifacts alone*.

> **Lemma (Flattening Enables Laundering).** If a reactor's decision and effect surfaces are merged — flattening $\varphi(S)>0$ [1] — then $\exists e.\ \neg\,\mathrm{Reconstructable}(\mathcal{P}(e))$, so undetectable laundering is possible. Reactor non-flattening is a *necessary condition* for the first disjunct system-wide.

Read against the filtration, each species of laundering is a bypass of one specific containment, and the orientation duality (§4) gives the adversary its sharpest signature (§9): a control *modeled* as an enabler that *behaves* as a no-op gate. Laundering is the authority-axis form of a substrate-level pathology that appears, on the coherence axis, as the hallucination and *Governance Failure* of *Semantic Manifold Competence* (SMC §8.2, App. C) — locally admissible, globally off-warrant; see §19.

---

## **7. Governance as Compilation**

The filtration descends a representational stack — $\text{Language}\to\text{Meaning}\to\text{Structure}\to\text{Authority}\to\text{Procedure}\to\text{Effect}$ — a lowering pipeline in the compiler sense.

> **Laundering as Illegal Lowering.** Authority laundering is an illegal lowering: a transition whose lowered form carries more binding force than its source licensed, with no admission accounting for the increase.

> **Correspondence (Warrant : Effect :: Type : Value).** A type error claims a value inhabits a type it does not; laundering claims an effect carries a warrant it does not. Type soundness's two halves — *progress* and *preservation* — become **liveness** (warranted proposals can reach effect) and **warrant preservation** (no transition increases binding force without admission). Laundering is a failure of warrant preservation.

> **Capability Containment.** For a procedure $p$ lowered from meaning $m$, $\mathrm{Cap}(p)\subseteq\mathrm{Cap}(m)$. Violation is procedural authority laundering. Governing constraint: legitimacy is preserved downward or not at all — every stage may narrow binding force; none may widen it except admission, and only with a receipt.

---

## **8. The Matrix of Laundering**

The matrix is the filtration of §3 read as a grid: which containment (invariant) is violated, at which stage. Four invariants plus one cross-cutting constraint suffice.

> **The Invariants.** **(I) Identity preservation.** **(II) Semantic preservation** (projection, binding). **(III) Monotonicity** (no unauthorized widening). **(IV) Causal necessity** (admitted authority is constitutive). Cross-cutting: **(V) Non-interference (isolation)** — transitions outside a stage do not alter its authority conditions; (V) is a global constraint, and its violation is the seam through which compositional laundering (§13) enters.

> **Laundering as a Matrix Cell.** $\mathrm{Laundering} = \mathrm{Violation}(\text{Invariant}, \text{Stage})$. Each construct enforces one cell.

| Stage | Invariant | Laundering signature | Guard / Filter |
|---|---|---|---|
| Identity | I | semantic smearing, coordinate shadowing | SCIT, GTK |
| Projection | II | translation / embedding laundering | Constitutional Legends |
| Binding | II | ungoverned anchor selection | CBT |
| Cooling | III | posture / scope laundering, authority smuggling | GCNL |
| Crystallization | III, IV | latent token read as effective | CSC |
| Coverage | III, IV | governance absence vs. failure | GCG |
| Admission | III, IV | off-warrant effect (escalation) | CARA |
| Continuity (artifact) | I | semantic mutation under presumed persistence | CSH |
| Continuity (actor) | I | attribution laundering, identity substitution | Proof-Carrying Identity |
| Continuity (memory) | IV | recall read as authorization | GCM |
| Context | IV | availability read as admissibility | CCM |
| Procedure | III | capability widening in lowering | GCML |
| Execution | III, IV | runtime success read as authority | Machine Closure |
| Reachability | IV | ceremonial authority (governance theater) | CSoftA |

> **Localization.** Every species of laundering localizes to exactly one cell. The Semantic Operating System (SOS) is the runtime enforcing the whole grid — append-only, non-bypassable, replayable, authority-monotonic, $\tau$-decomposable — with closure $\mathrm{Authority}_{\mathrm{eff}} \subseteq \mathrm{Authority}_{\mathrm{lat}}$.

> **Lemma (Filtration Irreducibility) — proof obligation.** *Claim:* under non-redundancy of guards, the filtration is irreducible — each filter is necessary, in that removing its guard while holding the others fixed admits a laundering witness ($\forall c,\ \exists e$ reachable off-warrant at $\mathrm{Guard}(c)$), and no filter's cell is covered by another's. This would establish the constructs as a *minimal* covering set rather than a chosen vocabulary, and is the formal answer to the "branded ontology" charge. It is stated here as a proof obligation, not a result: a complete proof is a finite, per-cell structural argument — exhibit, for each cell, the witness its guard's removal admits — and is the central consolidation task the theory still owes. Its empirical shadow is already runnable: in a deterministic projection (Appendix C) the witness for each removed guard is produced by the per-construct removal test, so the coverage frontier *is* the irreducibility claim under test.

---

## **9. The Adversary**

Perception is a projection over the legitimacy-chain artifacts of §6, not a mental state:
$$\mathrm{Perceived}(A) := \{\, e \mid \exists\,\pi\in\mathcal{P}(e)\text{ whose artifacts assert } A \,\}.$$

> **Definition (Launderer).** A launderer maximizes the gap between perceived and actual authority,
> $$\max_{e}\ \mathbf{1}\!\left[e\in\mathcal{R}(S\mid\neg A)\right]\wedge\mathbf{1}\!\left[e\in\mathrm{Perceived}(A)\right] \;=\; \mathrm{Perceived}(A)\setminus\mathrm{Authority}(A).$$

This subsumes the threats a frontier system faces: **prompt injection** (effects reachable without intended admission, perceived as instruction-governed); **context poisoning / retrieval spoofing** (effects in $\mathrm{Perceived}(A)$ but not $\mathrm{Authority}(A)$); **tool over-permissioning** (capability widening enlarging the $A$-free reachable set); **guardrail theater** (the defender's own contribution to the gap).

> **Laundering as Orientation-Confusion.** Authority laundering is the conflation of the two orientations (§4): a control modeled as an enabler that behaves as a trivial gate — $\mathrm{Perceived}(A)\neq\emptyset$ yet $\mathrm{Authority}(A)=\emptyset$. Guardrail theater is the pure case; a ceremonial admission gate is the same pathology one stage upstream. The defense objective is dual: drive $\mathrm{Perceived}(A)\setminus\mathrm{Authority}(A)$ to empty.

> **Non-uniqueness as attack surface.** When $|\mathcal{P}(e)|>1$, an adversary may exhibit a witnessed but non-minimal path to satisfy reconstructability while the effective cause lies off it. Robust warranting binds to $\pi_e^{*}$ or requires *all* admissible paths be constitutive.

---

## **10. The Removal Test and Its Falsification**

> **Removal-Test Protocol.** To test $(e,A)$: (1) compute $\mathcal{R}(S)$, confirm $e\in\mathcal{R}(S)$; (2) form $S\mid do(\neg A)$; (3) recompute $\mathcal{R}(S\mid do(\neg A))$ (exactly if bounded-deterministic; via $\mathcal{R}^{\sharp}$ otherwise); (4) test membership. If $e\in\mathcal{R}(S\mid do(\neg A))$, $A$ is ceremonial for $e$.

> **Minimal Ceremonial Witness.** A system exhibits ceremonial authority iff $\exists e.\ e\in\mathcal{R}(S)\wedge e\in\mathcal{R}(S\mid do(\neg A))$. This single witness makes laundering posture benchmarkable: count the cells of §8 admitting one.

> **Ceremony is Inspection-Invisible.** Whether $A$ is constitutive cannot be decided by inspecting $A$ alone; it is a property of $\mathcal{R}$, recoverable only by the removal test or sound static analysis.

> **The Builder's Trap.** Observing $e\in\mathcal{R}(S\mid do(\neg A))$ for a *proposed* control is evidence it would be ceremonial *as proposed*, not that it is unnecessary — opposite conclusions. The fix is to make $A$ constitutive (route $e$ through it), not to decline to build it. Appendix C records committing and correcting this error.

---

## **11. The Prevention Theorem**

> **Prevention Theorem (three conditions).** $S$ is laundering-free iff every binding transition $t$ satisfies all three: **(1) Validity** — $t$ preserves invariants I–IV at its stage, the invariant-IV conjunct being the reachability criterion (every admitted effect unreachable absent its admission); **(2) Trace** — $t$ emits $\tau_t=(EP,GR,ER)$ composing into a complete external lineage; and **(3) Intent-coverage** — every admitted effect lies in $\mathcal{R}_{\mathrm{int}}(I_A)$ (caused effects are willed). The conditions defeat the three disjuncts of §6 respectively: (2) makes warrant reconstructable (disjunct one), (1.IV) makes authority constitutive (disjunct two), (3) makes authority willed (disjunct three). Condition (3) is vacuous absent intent records, recovering the original two-condition theorem. *(Proof below.)*

**Proof.** Write a binding effect $e$ as the terminus of a chain of binding transitions $t_1,\dots,t_n$. By §6, $\neg\mathrm{Laundered}(e,A)\iff \mathrm{Reconstructable}(\mathcal{P}(e))\wedge e\in\mathrm{Authority}(A)\wedge e\in\mathcal{R}_{\mathrm{int}}(I_A)$, and $S$ is laundering-free iff this holds for every binding $e$. ($\Leftarrow$) Assume (1)–(3) at every binding transition. Along the chain producing $e$: by (2) the emitted $\tau_{t_i}$ compose into a complete external lineage, so $\mathrm{Reconstructable}(\mathcal{P}(e))$; by (1.IV) each admission leaves its effect unreachable absent that admission, so $e\in\mathrm{Authority}(A)$; by (3) each step's effect lies in $\mathcal{R}_{\mathrm{int}}(I_A)$, which — being the closure of the recorded intents under the admissible relation $\vdash$ — contains the composed $e$, so $e\in\mathcal{R}_{\mathrm{int}}(I_A)$. All three conjuncts hold, so $\neg\mathrm{Laundered}(e,A)$; as $e$ was arbitrary, $S$ is laundering-free. ($\Rightarrow$) By contraposition, a failure of any one condition exhibits a laundered effect: a (2)-failure yields binding $e$ with $\neg\mathrm{Reconstructable}(\mathcal{P}(e))$ (disjunct one); a (1.IV)-failure yields $e\notin\mathrm{Authority}(A)$ (disjunct two); a (3)-failure yields admitted $e\in\mathrm{Authority}(A)$ with $e\notin\mathcal{R}_{\mathrm{int}}(I_A)$ (disjunct three). Each makes $S$ not laundering-free, so laundering-free implies all three. $\square$

The third conjunct composes *only* because $\mathcal{R}_{\mathrm{int}}(I_A)$ is defined as a $\vdash$-closure — the same definitional choice that makes membership decidable (§12). The theorem therefore holds at exactly the rigor of the original two-condition form, and the teleological disjunct's membership test $e\in\mathcal{R}_{\mathrm{int}}(I_A)$ is decidable on finite deterministic systems by the §12 fixpoint argument — discharging both obligations the repair reopened.

A system emitting perfect lineage while admitting everything is fully traceable and fully laundered; one gating everything while emitting no lineage is fully constitutive and fully unauditable. Only the conjunction is laundering-free.

> **Corollary (Posture as a Vector).** Laundering posture is a vector over the cells of §8, each in {constitutive-and-traced, traced-only, constitutive-only, unguarded}, computed by the removal test (constitutive?) and trace reconstruction (traced?). This vector is the governance KPI a program drives toward *constitutive-and-traced*.

---

# **Part III — Realization**

## **12. Deterministic First**

The decidability boundary (§2) dictates the adoption order, and the order is the business case.

**Phase 1 — Deterministic infrastructure (provable).** Build systems, CI/CD, deployment and release tooling, policy engines, infrastructure-as-code, and the governance tooling itself are finite, deterministic projections of the GSOS. There the removal test is *exact*: two-sided, provable laundering-freedom per transition, with a full $\tau$-lineage. These are also where laundering is quietly expensive — an unwarranted deploy, an escalated pipeline credential, a release whose approval gate was ceremonial. Phase 1 yields immediate, auditable wins and a working posture vector with no approximation.

**Phase 2 — Bounded extension.** Orchestrators, agent frameworks with constrained tool sets, retrieval pipelines admit the static form: $\mathcal{R}^{\sharp}$ over-approximates, proving non-laundering where the abstraction permits and abstaining honestly elsewhere. Abstention entries localize where authority cannot yet be certified.

**Phase 3 — Learned systems (over-approximation).** For models proper, exact reachability is undecidable, but the framework applies through architectural enforcement: route every model-mediated effect through an admission stage whose removal is provably blocking — a deterministic gate around a stochastic core. The model's outputs become *proposals*; admission, deterministic and traced, confers effective authority. This converts an undecidable interior into a decidable perimeter — the Phase-1 construction at the boundary of the learned component.

The arc is "deterministic governance *around* AI," earned by proving the instrument where it is exact.

---

## **13. Compositionality and the Open Frontier**

> **Compositionality (partial result + open problem).** Laundering-freedom does not compose in general: composing two laundering-free subsystems can create cross-system effects reachable through neither alone, reintroducing a constitutive-but-untraced cut at the seam — a violation of non-interference (V). A *sufficient* condition: if $S_1, S_2$ (i) share no latent authority, $\mathrm{Authority}_{\mathrm{lat}}^{S_1}\cap\mathrm{Authority}_{\mathrm{lat}}^{S_2}=\emptyset$, and (ii) admit no cross-system path firing without joint admission, then the composition is laundering-free and authority is additive, $\mathrm{Authority}_{S_1\parallel S_2}(A)=\mathrm{Authority}_{S_1}(A)\cup\mathrm{Authority}_{S_2}(A)$. The general *static-verification* case — proving a composition laundering-free from the parts and seam without global recomputation — remains the central open question for scaling the guarantee, the place the broader semantic-transformation theory must do its hardest work: composing projections of the GSOS without leaking reachability across the seam.

> **Runtime-prevention corollary (PROV).** The *prevention* of general compositional laundering, as distinct from its static verification, is achievable by a deterministic runtime policy. Let every transition exercising authority $A$ emit an admission record $\mathrm{adm}(A)$, let cross-system paths propagate the accumulated set $\mathrm{ProvSet}$, and let every producer of a binding effect $e$ fire only if $\mathrm{adm}(\mathrm{req}(e))\in\mathrm{ProvSet}$ — an authority-scoped re-check at the producer. Then every binding $e$ satisfies the cut-set criterion: under $do(\neg\mathrm{req}(e))$ no path carries $\mathrm{adm}(\mathrm{req}(e))$, so the producer never fires and $e\notin\mathcal{R}(S\mid do(\neg\mathrm{req}(e)))$ — and because the argument turns only on the producer re-check, it holds even when subsystems share latent authority. The sufficient condition above is the special case in which $\mathrm{ProvSet}$ carries no cross-authority and the producer re-runs its own gate; PROV strictly generalizes it, admitting laundering-free shared-authority compositions that condition rejects while blocking shared-authority bypasses at the producer. The propagated $\mathrm{ProvSet}$ is exactly a provenance-bearing token and the producer re-check is its authority-scoped verification: deterministic prevention and long-horizon auditability are one mechanism. Correctness is relative to faithful authority-scoping — a mis-scoped shared authority defeats it — and the *static* modular verification of the same property remains open.

---

## **14. Synthesis: Authority as Governed Reachability across a Semantic Manifold**

The thesis is now fully discharged rather than asserted. *Semantic manifold* (§2) is the space; *reachability* (§2, §4) is the operator and the cut-set; *governed* (§3) is the filtration — identity, projection, binding, validity, admissibility — that carves authority out of raw reachability. Authority is the bottom of that filtration: admissible semantic reachability. Laundering is an effect that reaches the bottom by skipping a containment — reachable off-warrant, or untraceable — the appearance of governed reachability without the manifold-preserving transformations that earn it. Authority laundering is thus the first theorem of legitimacy-preserving semantic transformation: the failure that the whole filtration exists to prevent. The space named here is the object formalized as *Semantic Manifold Topology* (SMT), the layer governing continuity across transformation; ALT supplies the authority under which SMT admits those transformations (§19).

---

# **Part IV — Lineage and Authority Across Change**

## **15. Constitutional Lineage: Ostrom's Rule Hierarchy and the Causal Cut-Set**

The term *constitutional* and the cut-set construction are inherited, not coined; naming their lineage fixes both the vocabulary and the warrant for it.

**The constitutional level, precisely.** Kiser and Ostrom (1982), formalized in Ostrom (2005, ch. 2), distinguish three nested levels of rules in any governed system. *Operational* rules shape everyday action and its outcomes; *collective-choice* rules shape the structure and use of operational rules; *constitutional-choice* rules shape the structure and use of collective-choice rules — which actors have standing in which decisions, and which institutional mechanisms are available to them. Higher levels have wider scope and greater resistance to change, and the levels are nested. This is the precise sense intended here: the constitutional layer is the rules governing legitimate change to a system's own governing rules. The four jointly-necessary components named above — interpretation regime, admissibility law, authority binding, lineage continuity — are Ostrom's constitutional-choice level transposed from human institutions managing physical resources to systems managing authority.

**Convergence.** Ostrom's eight design principles for durable commons (Ostrom 1990) were obtained *inductively*, from comparative meta-analysis of long-standing common-pool-resource case studies; the principles here are obtained *deductively*, from the reachability filtration. They land in the same place, specifically:

| Ostrom design principle (1990) | Construct in this theory |
|---|---|
| Clearly defined boundaries | scope of the authority cut-set; receipt jurisdiction |
| Congruence / proportionality | admissibility law fitted to the governed transitions |
| Collective-choice arrangements | authority binding — who may admit or define |
| Monitoring | the reconstructability requirement (warrant witnessed from artifacts) |
| Graduated sanctions | admissibility enforcement and refusal |
| Conflict-resolution mechanisms | lineage / replay as the dispute record |
| Recognition of rights to organize | delegated authority under a higher binding |
| Nested enterprises (polycentricity) | the projection/substrate hierarchy; cross-system composition under joint admission |

Two independent derivations — one empirical, one formal — converging on the same governance principles is evidence for both. Ostrom established *that* durable governance requires monitoring, bounded scope, and nested authority; the construction here derives *why*, from the structure of reachability, and supplies the instrument her empirical program could not: a decidable test (§10) for whether a control is constitutive or merely ceremonial. The nesting principle is the sharpest correspondence: her finding that durable large-scale commons are organized as nested, polycentric enterprises is the institutional shadow of the compositionality result (§13) — authority that holds within a unit must be re-established across units, or it leaks at the seam.

> **Two anchors, one thesis.** The central identity of §14 — *authority is governed reachability across a semantic manifold* — has a recognized intellectual parent for each of its load-bearing words. **Governed** is Ostrom: the institutional-economics account of what makes a rule operative rather than advisory, and of the constitutional layer that governs legitimate change. **Reachability** is causal: the cut-set is computed under Pearl's intervention operator $do(\neg A)$ (Pearl 2009), the interventional contrast — the "doing" rung, distinct from rung-3 counterfactual imagination — at the center of structural causal inference. The removal test is that operator made into a governance instrument. The contribution is their composition — a causal cut-set applied to Ostrom's constitutional layer — yielding a deterministic, runnable criterion for laundered authority.

**Scope (honest).** Ostrom's principles have already been carried into digital and information commons — open-source governance, data commons, digital public goods — so the move from physical to computational governance is established, not novel here. What is new is the formalization: a single criterion (admissible reachability), a falsifiable test (removal), and a decidability result that makes the criterion exact on the deterministic systems where most authority flows. The mapping is structural — Ostrom studied humans governing physical resources; this theory governs authority in machines — and the shared object is the constitutional rule-layer and its design principles, not an identity between the domains.

---

## **16. Canonical Identity: Key-Derived Namespaces and Composite Provenance**

The projection filter (§3; invariant II of §8) demands that authority survive a change of representation, which is verifiable only if the cut-set is expressed over identities that do not drift with representation. The corpus supplies the cryptographic realization. Identities are *derived from their constitutional inputs* rather than assigned by an operator: a DKN (Distributed Knowledge Network) dimension address is `dimension_id = BLAKE3(phase_code ‖ governor_pubkey)`, and a participant identity is `MosaicID = BLAKE3(ed25519_pubkey)` — neither squattable nor operator-revocable without the controlling key. Because each address is a function of the governing authority, the namespace is self-sovereign and representation-independent: the same identity denotes the same object across stores, grains, and policy models.

The semantic-axis realization of the same canonical identity is a **SCIT** coordinate (*Semantic Coordinate Identity Tokenization*): a governed coordinate that is identity, address, and topological location at once, distinguishing *semantic identity* from *semantic surface* exactly as this theory distinguishes authority (the cut-set) from artifact (its representation). A SCIT coordinate already *carries* the warrant the cut-set must be expressed over — its standing properties include governance metadata, revision lineage, and jurisdictional scope (SCIT App. B) — so the identity layer ALT requires is not something it must construct. The cryptographic key-derived identifiers above and the SCIT coordinate are one canonical identity seen on the cryptographic and semantic axes (§19).

Provenance is correspondingly composite. The three-hash doctrine identifies an artifact by continuity, state, and meaning at once — `session_id_csh + state_hash + semantic_hash` — and Cryptographic Homological Compilation (CHC) folds object, lineage, and governance into a single Level-2 commitment over the Level-1 byte hash. The continuity strand (CSH) binds an artifact to its warrant across time; the meaning strand (the DKN semantic hash) makes the warrant *portable* across representation; CHC binds the whole multidimensionally. Key-burn — destroying a dimension's authority key after population — is the maximum-strength form: contents become cryptographically immutable, and constitutional drift becomes detectable against a public immutable record. This is the identity layer over which the cut-set must be expressed for the projection filter to hold; an access entry recorded only in a store-native form has, by contrast, persisted a projection of its authority and not the authority itself.

> **Identity across amendment (representation-independence is not yet continuity).** The key-derived address fixes identity across *representation* at a moment — what the projection filter (§3) needs — but not across *amendment* over time, which §17 needs, and the two naive answers both fail the laundering test. A bare label ("same name, therefore same authority") persists while the warrant is silently swapped — authority-by-proximity, laundering by continuity of label. A hash of *all* constitutional inputs fractures — every legitimate amendment yields a new address, so no authority survives its own amendment and §17 has nothing to compare. Canonical identity must lie between: stable under legitimate evolution, broken under illegitimate substitution.

> The resolution defines identity by the *transformation*, not the endpoints. Let $A\equiv A'$ iff $A'$ is reachable from $A$ by a chain of **legitimacy-preserving amendments** — amendments meeting the four-fold condition of §11 (reconstructable ∧ caused ∧ valid ∧ intent-covered). The canonical identity of $A$ is the equivalence class $[A]$ under $\equiv$, addressed by the key-/SCIT-coordinate computed over the **invariant core** — the subset of $A$'s specification legitimacy-preserving amendments must hold fixed — rather than over the full, amendable content: $\mathrm{CanonicalID}(A)=\mathrm{SCIT}\big(\mathrm{invariant\_core}(A)\big)$. Amendments preserving the core preserve the address (continuity); substitutions changing the core change it, so the warrant change is *visible* rather than laundered. This is decidable on finite deterministic systems — $\equiv$ is a $\vdash$-closure as in §12 and address equality is hash equality — **relative to a declared invariant core.** *(Open obligation: which subset is identity-bearing is a per-system specification choice — too small lets substitutions pass as "the same authority" (laundering), too large fractures legitimate amendments — so canonical identity is decidable relative to that schema, not absolutely; the theory localizes the judgment, it does not remove it.)* ALT does not construct the coordinatization — SCIT does (§19) — but it must declare this projection, and that declaration is ALT's side of the ALT↔SCIT seam. Identity so defined is the invariant under the legitimacy-preserving transformation group: "what transformations preserve authority" applied to the authority itself, and the precondition §17 requires to compare cut-sets across versions.

## **17. Policy Evolution: Cross-Version Authority Comparison**

Portable governance models evolve, so comparing policies authored under different governance versions must be well-defined. The cut-set already supplies the comparison. By Authority Equivalence (§4), two policies are the same authority iff they cut the same effects; by Monotonicity (§4), authorities are partially ordered by cut-set containment. A version change is therefore *classified*, not merely flagged, by the difference of the two cut-sets over a common identity space:

> **Classification of a version change.** Effects in v2's cut-set but not v1's are newly granted — a widening, and the place cross-version laundering hides. Effects in v1's but not v2's are dropped — an authority loss. Both empty: the change is authority-preserving. Both non-empty: *incomparable* — the dangerous case, localized exactly by the difference.

This is the removal-test certification of §10 lifted from across-representations to across-versions, with the same prerequisite: the cut-sets must live over a common, version-stable identity space (§16), bridged by a map where the versions' effect vocabularies differ. Two boundaries follow. First, governance versions must themselves be identified — they are hash-stable constitutional commitments (frozen-compiler form), so a cross-version comparison is a comparison against two named commitments. Second, when v2 *expands the effect ontology* — introduces a dimension of authority that v1 could not express — v1 policies are silent in the new dimension; the comparison detects and localizes the silence but cannot fill it. Resolution is fail-closed by default, or by the will (§18) re-evaluated against the expanded space.

> **§18 synchronization — temporal-reuse independence (Temporal-PROV, O6).** *(Doctrine sync; annotation, not a new disjunct.)* Laundering-via-reuse (disjunct (b) over time, per the §6 synchronization) governs an **independent domain**: temporal reuse boundaries and §13 producer seams are *distinct objects that instantiate the same constitutional re-derivation obligation* (O2/H_rel), and neither subsumes the other (O6 — a static-composition laundering instance with no temporal reuse, and a temporal-reuse instance with no composition seam, both exist). The taxonomy therefore remains the three mechanism-classified disjuncts (epistemic / causal / teleological); temporal reuse is recorded as an independent *domain* exercising the causal mechanism, not as a fourth disjunct.

## **18. The Will: Intent as a Re-Derivable Layer**

Above the canonicalized policy sits a further layer, distinguished from the cut-set as *intension* from *extension*. The cut-set is extensional: it enumerates *which* effects are authorized, in one identity space, at one moment. The **will** is intensional: it states *why* — the purpose the policy serves — from which a cut-set can be re-derived. The cut-set is the will evaluated against a representation; the will is the generating function, the cut-set its value. Persisting only the value lets one re-express authority wherever the identity space is preserved; persisting the function lets one *re-evaluate* it for a genuinely different representation.

This is the layer that governs recovery. The cut-set suffices to *detect* loss and *certify* preservation, and those stay decidable. But when a projection (§16) or a version change (§17) cannot preserve the cut-set exactly, the cut-set alone cannot say what the correct policy in the new space is; the will can, because it carries the intent the new cut-set must realize. Recovery is then propose-then-admit: regenerate a candidate cut-set from the will — a proposal, possibly human- or model-assisted, hence expensive — then re-admit it deterministically, which is cheap and certifiable.

> **Caution.** The will is the most meaning-bearing and least decidable layer. It must sit strictly above the deterministic core: the cut-set remains the decidable certification layer, and the will is the recovery aid that turns the expensive human step from intractable to tractable. The legitimacy chain's Proposal link (§6) is the will at creation; this layer is its upgrade — from an audit record that admission occurred to a re-executable generating specification.

> **Formal layer (decidable membership vs. expensive generation).** Recorded as $I_A$, the will generates the intended-reachable set $\mathcal{R}_{\mathrm{int}}(I_A)$ (§6); an effect is *will-consistent* iff $\mathrm{Rederivable}(e,I_A)$, and a caused-but-unwilled effect ($e\in\mathrm{Authority}(A)\wedge e\notin\mathcal{R}_{\mathrm{int}}(I_A)$) is the teleological disjunct of §6. Two operations must be kept apart, and only one is expensive. *Generation* — regenerating a cut-set from the will for a genuinely new representation (§16–§17 recovery) — is the least-decidable step the Caution names, and is unchanged. *Membership* — testing $e\in\mathcal{R}_{\mathrm{int}}(I_A)$ against existing records — is a closure-membership query, decidable on finite deterministic systems by the same construction as $\mathcal{R}(S)$ (§12). The laundering test uses membership; the recovery aid uses generation, so the Caution stands for generation while the new disjunct stays decidable. Legitimacy is then four-fold: $\mathrm{Legitimate}(e,A)\iff \mathrm{Reconstructable}(\mathcal{P}(e))\wedge e\in\mathrm{Authority}(A)\wedge e\in\mathcal{R}_{\mathrm{int}}(I_A)$ — traceable, caused, and willed. The legitimacy structure is thus **two-axis**: the structural filtration of §6 ($\text{identity}\supseteq\cdots\supseteq\text{admissibility}$) is one axis, and intent-coverage is a second, *orthogonal* gate — not a further containment in the chain, since by the §6 independence an effect can be admitted yet unwilled (intent laundering) or willed yet unadmitted (unrealized intent).

---

## **19. Co-Projection as a Decidable Admissibility-Homomorphism**

The companion theories — SCIT, SMT, SMC, and the §15 rule-hierarchy — are often read as a stack ALT sits within, or as projections of a common substrate ALT helps coordinatize. Both framings invite more metaphysics than the result supports. The defensible claim is smaller and checkable, and it is best stated in the program's cartographic terms: **theories are charts, and a correspondence between them is a transition map.**

Coordinatize a theory $T$ as a typed graph $G_T$ — constructs as nodes, paper-declared typed relations as edges — and let its **admissibility subgraph** $G_T^{\mathrm{adm}}$ be the subgraph on the admitting relations (the `ENABLES`/`GOVERNS` edges a governance check treats as conferring admissibility, all else fail-closed). A **co-projection** $\varphi : T \to T'$ is a map of constructs that is a homomorphism on the admissibility subgraphs — every $u\xrightarrow{k}v$ in $G_T^{\mathrm{adm}}$ has $\varphi(u)\xrightarrow{k}\varphi(v)$ in $G_{T'}^{\mathrm{adm}}$ — that does **not** extend to a homomorphism of the full graphs. The preserved part is the shared admissibility structure; the unpreserved part is each theory's private neighborhood. This is exactly a chart transition map in the atlas sense (§14, and GSC §14): $\varphi$ says how one theory's coordinates translate into another's where they overlap, and the overlap is precisely the admissibility core.

**The relationship is decidable.** Verifying a proposed $\varphi$ is linear in $|E^{\mathrm{adm}}|$ — check each admissibility edge maps to one and confirm at least one neighborhood edge fails to — and it is the procedure the corpus already runs: the bridge evaluator's admissibility check, which admits a relation iff an `ENABLES`/`GOVERNS` edge is declared and fails closed otherwise. So a proposed correspondence between theories can be *proposed, checked, and refused* rather than asserted — the propose-then-admit posture of the will (§18), lifted to inter-theory structure.

**One instance, on scratch.** Run against ALT and SMC, each rendered with only its own paper's typed edges, the check preserves *exactly* the admissibility relations and nothing else: a mechanism-named typing carries the admissibility-bypass relation across (laundering ↔ SMC's *Governance Failure*) while detection, the integrity violated, and each theory's taxonomy stay private. A coarser four-kind typing preserves twice as much, *overstating* the overlap — itself a caution that coarse vocabulary launders analogy as structure. The verdict is alignable-on-the-shared-primitive (necessary, not sufficient), not isomorphic: the signature of co-projection. The check ran on a scratch coordinatization; the canonical meaning base encodes none of these constructs.

**Scope, held tight.** This supports one claim — that ALT's admissibility core and a partner theory's are the same finite structure up to a decidable homomorphism, neighborhoods private — and refuses its inflation. Formalizing the would-be "substrate" deflates it: once it is *defined* as the shared admissibility core, it is a derived common-core, not a foundation any theory is a coordinate system *for*. The wider picture — one substrate on several axes, the coordinatization of SCIT, SMT, and GSC that would instantiate it, and the substrate-ontology aspiration — is architecture pending construction, developed in the companion (*ALT Co-Projection: Architecture and Coordinatization Roadmap*), not asserted here.

> **Co-projection between coordinatized theories is a decidable admissibility-homomorphism problem.** Everything beyond it — the multi-axis substrate, its ontology, and the coordinatization that would instantiate it — is a research program, not a result of this theory.

---

## **Conclusion**

Legitimacy is a filtration, not a label: a system's semantic reachability is narrowed by identity, projection, binding, validity, and admissibility, and authority is what survives. From this single picture, authority laundering is the effect that skips a filter while wearing the output's legitimacy, detectable by three independent tests — its path cannot be reconstructed, it survives removal of its claimed authority, or (where intent is recorded) it falls outside the authority's will. The resolution is to make every binding effect both reconstructable and counterfactually dependent on its authority: an authority is real only to the extent that its absence is felt. The instrument is runnable — remove the authority, recompute reachability, check membership — exact on deterministic projections of the governed semantic operating system and soundly approximated beyond them, which makes "deterministic first, learned systems around a deterministic perimeter" not a compromise but the theorem's natural deployment. Authority laundering is the first theorem of this filtration, and the general theory of legitimacy-preserving semantic transformation is the program it opens — including the conjecture, developed in the companion rather than established here, that the corpus's many constructs share one filtration over a common state graph. Part IV situates the result and extends it across change — its lineage in Ostrom's constitutional rule-hierarchy and Pearl's causal cut-set (§15), and the life-cycle of authority under representation, version, and recovery (§16–§18).

---

\newpage

## **Appendix A — The Filtration as a Transition Map**

$$
\mathcal{R}_{\mathrm{sem}}
\xrightarrow[\text{SCIT/GTK}]{\text{identity}}
\mathcal{R}_{\mathrm{id}}
\xrightarrow[\text{Legends}]{\text{projection}}
\mathcal{R}_{\mathrm{proj}}
\xrightarrow[\text{CBT}]{\text{binding}}
\mathcal{R}_{\mathrm{bind}}
\xrightarrow[\text{wf}]{\text{validity}}
\mathcal{R}_{\mathrm{lat}}
\xrightarrow[\text{CARA},\ \sigma]{\text{admission}}
\mathcal{R}_{\mathrm{eff}} = \mathrm{Authority}.
$$

Admission is the unique stage carrying latent to effective; it widens effective authority only within the latent set, and only by emitting $GR$. Every other stage narrows or holds. Each containment is a place the single discipline can be bypassed — the matrix cells of §8.

---

## **Appendix B — The Corpus as the Filtration**

Each construct is one filter of the chain (or the runtime enforcing all of them), and a projection of the GSOS fixing $S$ to its concern.

- **SCIT / GTK** — identity filter $\mathcal{R}_{\mathrm{id}}$: authority transitions between governed bindings, not words.
- **Constitutional Legends** — projection filter $\mathcal{R}_{\mathrm{proj}}$: authority is re-warranted across translation/embedding.
- **CBT** — binding filter $\mathcal{R}_{\mathrm{bind}}$: authority begins in governed ambiguity-collapse.
- **GCNL** — cooling: posture may not strengthen without admission.
- **CSC** — crystallization: confers latent eligibility, not effective constraint.
- **GCG** — coverage: governance failure vs. absence.
- **CARA** — admission filter $\mathcal{R}_{\mathrm{adm}}$: the unique latent-to-effective selection.
- **CSH / Proof-Carrying Identity / GCM** — continuity (artifact / actor / memory): persistence of identity, attribution, and that recall is not authorization.
- **CCM** — context: availability is not admissibility.
- **GCML** — procedure: $\mathrm{Cap}(\text{procedure})\subseteq\mathrm{Cap}(\text{meaning})$.
- **Machine Closure** — execution: execution cannot bind.
- **SMC** — the semantic manifold itself: the space $\mathcal{R}_{\mathrm{sem}}$ within which all reachability is defined.
- **SOS** — the runtime enforcing the whole filtration; **GSOS** — the canonical $S$ of which each construct is a projection.
- **CSoftA** — reachability: the removal test; the framework's falsifiable core.

---

## **Appendix C — A Worked Instrument: The Removal Test in a Governed Runtime**

A governed command-line toolkit furnishes a deployed, deterministic projection of the GSOS, and a documented Builder's Trap.

Initially its dispatcher opened a governance receipt and closed it in the same step, stamping admission unconditionally — ceremonial authority: for every effect $e$, $e\in\mathcal{R}(S\mid do(\neg A))$ (removing the receipt changed nothing reachable). A first analysis concluded a real evaluation would be "ceremony" because the effects were already reachable without it — the Builder's Trap exactly.

The correction installed an admission evaluator *before* execution: it consumes intent, authority, and the operative law hash, evaluates blocking rules (law currency, chain integrity), records the verdict as $GR$, and refuses — the executor never runs — on an inadmissible verdict. The criterion was then discharged empirically: corrupting the receipt chain's tip and re-issuing a command produced a typed refusal with the tool never executing ($e\notin\mathcal{R}(S\mid do(\neg A))$), while an intact chain admitted and executed. The authority had moved from latent (present, inert) to effective (constraining), verified by removal rather than asserted by inspection — and because the projection is bounded and deterministic, the test was *exact*. The toolkit's per-construct coverage frontier is the posture vector of §11 made operational.

---

## **References**

[1] A. Ableman Mazurk. *Semantic Reactor Theory: Governance-Native Architecture for High-Authority Semantic Transformation Systems.* Working paper.

[2] B. C. Pierce. *Types and Programming Languages.* MIT Press, 2002. (Type soundness; progress and preservation as liveness and warrant preservation.)

[3] M. S. Miller. *Robust Composition: Towards a Unified Approach to Access Control and Concurrency Control.* PhD thesis, Johns Hopkins University, 2006. (Object-capability discipline; capability containment.)

[4] J. Pearl. *Causality: Models, Reasoning, and Inference.* Cambridge University Press, 2nd ed., 2009. (Intervention semantics; the $do(\cdot)$ operator.)

[5] P. Cousot and R. Cousot. *Abstract Interpretation.* POPL, 1977. (Sound over-approximation; the static reachability form.)

[6] J. H. Saltzer and M. D. Schroeder. *The Protection of Information in Computer Systems.* Proc. IEEE, 1975. (Least privilege; antecedent of authority monotonicity.)

[7] G. C. Necula. *Proof-Carrying Code.* POPL, 1997. (Antecedent of proof-carrying identity and warrant-by-structure.)

[8] A. Ableman Mazurk. *The CSoftA Corpus.* Internal corpus (the filters of the legitimacy filtration; projections of the GSOS).

[9] E. Ostrom. *Governing the Commons: The Evolution of Institutions for Collective Action.* Cambridge University Press, 1990. (The eight design principles; durable commons governance.)

[10] L. Kiser and E. Ostrom. *The Three Worlds of Action: A Metatheoretical Synthesis of Institutional Approaches.* 1982. (The operational / collective-choice / constitutional-choice rule hierarchy.)

[11] E. Ostrom. *Understanding Institutional Diversity.* Princeton University Press, 2005. (The IAD framework; rule levels, ch. 2.)