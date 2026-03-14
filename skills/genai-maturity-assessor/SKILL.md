---
name: genai-maturity-assessor
description: "Standalone Lite-mode GenAI maturity assessor with embedded question bank, scoring rubrics, and report template."
---

# GenAI Maturity Assessor (Lite-Only, Standalone)

Generated file. Do not edit manually; run the skill bundle sync command.

This file is intentionally self-contained for assistant UIs that ingest only one `SKILL.md`.

## Trigger Phrase

When a user wants to start an assessment, they can type exactly:

`assess my genai system`

## Runtime Contract

If external files are unavailable, run the assessment using the embedded configs in this file.

1. Do not invent interview questions.
2. Use exact prompts from `criticality_rules.yaml` and `interview_inference.yaml` below.
3. Respect all `ask_if` conditions exactly.
4. Accept unknown as `?` and score conservatively.
5. Infer gaps only from embedded inference rules.
6. Compute criticality, quality score, maturity level, priorities, and actions with the rules below.
7. Return the result in the report template below.

## Lite Mode Workflow

### Step 1: Capture Metadata
Ask one question at a time. Wait for the user's answer before asking the next question.

Ask:
- `System name`
- `Owner team`
- `Assessor name`
- `Assessment date` (default to today if not provided)

### Step 2: Ask Business Criticality Questions
Ask criticality questions one at a time in order, exactly as defined in `criticality_rules.yaml`.

### Step 3: Ask Capability Signals
Ask signal questions one at a time in order from `interview_inference.yaml`.

- For `bool`: accept `y`, `n`, `?`
- For `int`: accept integer or `?`
- For `float`: accept number or `?`
- For `enum`: accept listed option or `?`
- If `ask_if` is false: skip question and set signal to unknown (`None`)

### Step 4: Infer Gaps (`no` / `small` / `large`)
For each sub-characteristic:
- If `full_condition` is true: gap = `no`
- Else if minimal requirement exists and `min_condition` is true: gap = `small`
- Else: gap = `large`

Unknown handling:
- If any referenced signal is unknown in a condition, treat that condition as false.
- Add rationale suffix: `Some answers were unknown and were scored conservatively.`

Rationale text per inferred gap:
- `no`: `Full requirement is currently demonstrated.`
- `small`: `Minimal requirement is demonstrated, but full requirement is not yet demonstrated.`
- `large` with minimal requirement: `Neither minimal nor full requirement is currently demonstrated.`
- `large` without minimal requirement: `Full requirement is not yet demonstrated.`

### Step 5: Classify Criticality and Required Maturity
Use embedded `criticality_rules.yaml`:
- Not in production -> `proof_of_concept` -> required level `L1`
- In production and any critical trigger true -> `production_critical` -> required level `L5`
- Otherwise in production -> `production_non_critical` -> required level `L3`

### Step 6: Compute Scores and Maturity
Gap values:
- `no = 0`
- `small = 1`
- `large = 2`

Quality score:
- `quality_score = round(100 * (1 - sum(gap_values) / (2 * number_of_sub_characteristics)), 2)`

Characteristic score:
- Same formula, but only for sub-characteristics in that characteristic.

Gate satisfaction:
- gate `none`: always satisfied
- gate `min`: satisfied when gap in `['no', 'small']`
- gate `full`: satisfied when gap in `['no']`

Actual maturity:
- Highest level from L1..L5 where all sub-characteristics satisfy that level gate in `maturity_gates.csv`.

### Step 7: Build Priority Actions
For each sub-characteristic with unmet gate:
1. Find `first_unmet_level` = first level where gate is not satisfied.
2. Priority:
- `critical` if `first_unmet_level <= min(required_level, actual_level + 1)`
- `important` if `first_unmet_level <= required_level`
- `nice_to_have` otherwise
3. Determine action using `recommendations.yaml`:
- if target gate is `min`: use `min_action`
- if target gate is `full` and gap is `small`: use `full_action`
- if target gate is `full` and gap is `large` and minimal requirement exists:
  `Step 1: {min_action} Step 2: {full_action}`
- otherwise: use `full_action`
4. Sort by priority rank (`critical`, `important`, `nice_to_have`), then `first_unmet_level`, then name.

### Step 8: Output Report (Markdown)
Use this exact structure.

```md
# GenAI Maturity Assessment (Lite Mode)

## System Snapshot
- System: <system_name>
- Team: <owner_team>
- Assessor: <assessor>
- Assessment date: <assessment_date>
- Mode: Lite (no-code, Markdown-only)

## Business Criticality
- Classification: <Proof of Concept | Production Non-Critical | Production Critical>
- Required maturity level: L<required_level>
- Current maturity level: L<actual_level>
- Status: <Met required maturity | Below required maturity>

## Quality Overview
- Overall quality score: <quality_score>
- Utility: <score>
- Economy: <score>
- Robustness: <score>
- Productionizability: <score>
- Modifiability: <score>
- Comprehensibility: <score>
- Responsibility: <score>

## Priority Actions

### Critical
1. <DisplayName>: <action>

### Important
1. <DisplayName>: <action>

### Nice to Have
1. <DisplayName>: <action>

## Scoring Rationale (Inferred)
- <DisplayName>: <rationale>

## Notes
- Unknown (`?`) answers are scored conservatively.
- For JSON/CSV/HTML/PDF artifacts and CLI workflows, see `README.md`.
```

## Embedded Source Config Files

### criticality_rules.yaml
```yaml
required_maturity:
  proof_of_concept: 1
  production_non_critical: 3
  production_critical: 5

criticality_logic:
  production_key: in_production
  production_critical_if_any:
    - high_request_volume_top_third
    - dependent_teams_ge_4
    - revenue_impact_gt_1pct
    - strategic_importance

questions:
  - key: in_production
    prompt: Is the system currently in production? (y/n)
  - key: high_request_volume_top_third
    prompt: Is request volume in the top third of your production systems? (y/n)
  - key: dependent_teams_ge_4
    prompt: Do 4+ teams or products depend on this system? (y/n)
  - key: revenue_impact_gt_1pct
    prompt: Does it directly impact more than 1% of annual revenue? (y/n)
  - key: strategic_importance
    prompt: Is it strategically important (competitive or regulatory or high-consequence)? (y/n)
```

### interview_inference.yaml
```yaml
version: 1

signals:
  - key: golden_set_size
    type: int
    prompt: How many examples are in your golden evaluation set? (integer or ?)
  - key: eval_automated_metrics
    type: bool
    prompt: Do you run automated evaluation metrics on the golden set? (y/n/?)
    ask_if: golden_set_size >= 200
  - key: eval_human_review
    type: bool
    prompt: Is the evaluation validated with expert human review? (y/n/?)
    ask_if: golden_set_size >= 200
  - key: ab_experiment_positive
    type: bool
    prompt: Have you run an A/B experiment showing positive business impact? (y/n/?)
  - key: effectiveness_revalidated_after_changes
    type: bool
    prompt: Do you revalidate effectiveness after major model/prompt changes? (y/n/?)
    ask_if: ab_experiment_positive == true
  - key: latency_targets_tracked_and_met
    type: bool
    prompt: Are P95/P99 latency targets tracked and currently met? (y/n/?)
  - key: accessible_serving_infrastructure
    type: bool
    prompt: Is the system deployed in accessible serving infrastructure for intended users? (y/n/?)
  - key: costs_tracked
    type: bool
    prompt: Are the total GenAI system costs comprehensively tracked? (y/n/?)
  - key: value_exceeds_cost
    type: bool
    prompt: Is the measurable business value greater than the total system cost? (y/n/?)
    ask_if: costs_tracked == true
  - key: ops_automation_level
    type: enum
    options: [none, basic, full]
    prompt: Operations automation level for eval/prompts/knowledge refresh? (none/basic/full/?)
  - key: efficiency_optimized
    type: bool
    prompt: Are prompts/model routing/tuning optimized for cost-latency-performance tradeoffs? (y/n/?)
    ask_if: ops_automation_level in ['basic', 'full']
  - key: sla_with_fallback
    type: bool
    prompt: Does the deployed service meet defined SLA with fallback strategies? (y/n/?)
  - key: update_pipeline_success_rate
    type: int
    prompt: What is the automated update pipeline success rate per quarter (0-100, integer or ?)?
  - key: rollback_capability
    type: bool
    prompt: Do update/release pipelines support reliable rollback? (y/n/?)
  - key: behavior_update_manual_process
    type: bool
    prompt: Is there a documented manual process to update system behavior? (y/n/?)
  - key: behavior_update_automated_with_feedback
    type: bool
    prompt: Are behavior updates automated with user-feedback integration? (y/n/?)
    ask_if: behavior_update_manual_process == true
  - key: dynamic_scaling_with_controls
    type: bool
    prompt: Does the system dynamically scale with rate limits and cost controls? (y/n/?)
  - key: release_automation_level
    type: enum
    options: [none, partial, full]
    prompt: Release/update process automation level? (none/partial/full/?)
  - key: basic_monitoring_metrics
    type: bool
    prompt: Are core operational metrics monitored (latency/errors/throughput/tokens)? (y/n/?)
  - key: continuous_automated_evaluation
    type: bool
    prompt: Is continuous automated quality evaluation running in production? (y/n/?)
    ask_if: basic_monitoring_metrics == true
  - key: artifacts_versioned
    type: bool
    prompt: Are prompts and code versioned in source control? (y/n/?)
  - key: change_logs_with_rationale
    type: bool
    prompt: Are key artifact changes logged with rationale? (y/n/?)
    ask_if: artifacts_versioned == true
  - key: modularity_level
    type: enum
    options: [none, partial, full]
    prompt: Component modularity level for retrieval/prompting/post-processing? (none/partial/full/?)
  - key: test_coverage_percent
    type: int
    prompt: What is current automated test coverage percentage (0-100, integer or ?)?
  - key: integration_and_adversarial_tests
    type: bool
    prompt: Do tests include integration and adversarial cases? (y/n/?)
    ask_if: test_coverage_percent >= 80
  - key: versioned_releases_with_rollback
    type: bool
    prompt: Is production deployment versioned with rollback support? (y/n/?)
  - key: progressive_rollouts
    type: bool
    prompt: Do you use progressive rollouts for production changes? (y/n/?)
    ask_if: versioned_releases_with_rollback == true
  - key: runtime_kill_switches
    type: bool
    prompt: Are runtime kill switches available for rapid containment? (y/n/?)
    ask_if: versioned_releases_with_rollback == true
  - key: searchable_registry_entry
    type: bool
    prompt: Is the system registered in a searchable catalog with metadata and ownership? (y/n/?)
  - key: prompt_style_guide
    type: bool
    prompt: Do prompts follow a consistent style guide? (y/n/?)
  - key: unified_style_standards
    type: bool
    prompt: Are unified readability standards enforced for prompts and source code? (y/n/?)
    ask_if: prompt_style_guide == true
  - key: basic_metadata_logging
    type: bool
    prompt: Do you log prompt versions and core request metadata? (y/n/?)
  - key: end_to_end_lineage_tracking
    type: bool
    prompt: Do you track end-to-end lineage across prompts/models/context/tools/post-processing? (y/n/?)
    ask_if: basic_metadata_logging == true
  - key: documentation_level
    type: enum
    options: [none, partial, comprehensive]
    prompt: Documentation maturity level? (none/partial/comprehensive/?)
  - key: explainability_basic_signals
    type: bool
    prompt: Do outputs include basic reasoning or confidence signals where applicable? (y/n/?)
  - key: explainability_transparency_mechanisms
    type: bool
    prompt: Are user-facing transparency mechanisms implemented (citations/tool traces/confidence)? (y/n/?)
    ask_if: explainability_basic_signals == true
  - key: fairness_documented
    type: bool
    prompt: Are baseline fairness considerations explicitly documented? (y/n/?)
  - key: fairness_evaluated_with_mitigation
    type: bool
    prompt: Is performance evaluated across relevant groups with mitigations for disparities? (y/n/?)
    ask_if: fairness_documented == true
  - key: designated_owner_team
    type: bool
    prompt: Is a designated team accountable for operating and maintaining the system? (y/n/?)
  - key: standards_compliance_met
    type: bool
    prompt: Are applicable legal/regulatory/industry standards currently met? (y/n/?)
  - key: security_baseline_controls
    type: bool
    prompt: Are baseline security controls in place (sanitization, secret handling, injection checks)? (y/n/?)
  - key: security_multi_layer_with_adversarial_testing_and_audits
    type: bool
    prompt: Are multi-layer security controls in place with adversarial testing and regular audits? (y/n/?)
    ask_if: security_baseline_controls == true

sub_characteristics:
  accuracy:
    min_condition: golden_set_size >= 50
    full_condition: golden_set_size >= 200 and eval_automated_metrics and eval_human_review
  effectiveness:
    min_condition: ab_experiment_positive
    full_condition: ab_experiment_positive and effectiveness_revalidated_after_changes
  responsiveness:
    full_condition: latency_targets_tracked_and_met
  usability:
    full_condition: accessible_serving_infrastructure
  cost_effectiveness:
    min_condition: costs_tracked
    full_condition: costs_tracked and value_exceeds_cost
  efficiency:
    min_condition: ops_automation_level in ['basic', 'full']
    full_condition: efficiency_optimized and ops_automation_level in ['basic', 'full']
  availability:
    full_condition: sla_with_fallback
  resilience:
    min_condition: update_pipeline_success_rate >= 80
    full_condition: update_pipeline_success_rate >= 90 and rollback_capability
  adaptability:
    min_condition: behavior_update_manual_process
    full_condition: behavior_update_automated_with_feedback
  scalability:
    full_condition: dynamic_scaling_with_controls
  repeatability:
    min_condition: release_automation_level in ['partial', 'full']
    full_condition: release_automation_level == 'full'
  monitoring:
    min_condition: basic_monitoring_metrics
    full_condition: basic_monitoring_metrics and continuous_automated_evaluation
  maintainability:
    min_condition: artifacts_versioned
    full_condition: artifacts_versioned and change_logs_with_rationale
  modularity:
    min_condition: modularity_level in ['partial', 'full']
    full_condition: modularity_level == 'full'
  testability:
    min_condition: test_coverage_percent >= 50
    full_condition: test_coverage_percent >= 80 and integration_and_adversarial_tests
  operability:
    min_condition: versioned_releases_with_rollback
    full_condition: versioned_releases_with_rollback and progressive_rollouts and runtime_kill_switches
  discoverability:
    full_condition: searchable_registry_entry
  readability:
    min_condition: prompt_style_guide
    full_condition: prompt_style_guide and unified_style_standards
  traceability:
    min_condition: basic_metadata_logging
    full_condition: basic_metadata_logging and end_to_end_lineage_tracking
  understandability:
    min_condition: documentation_level in ['partial', 'comprehensive']
    full_condition: documentation_level == 'comprehensive'
  explainability:
    min_condition: explainability_basic_signals
    full_condition: explainability_basic_signals and explainability_transparency_mechanisms
  fairness:
    min_condition: fairness_documented
    full_condition: fairness_evaluated_with_mitigation
  ownership:
    full_condition: designated_owner_team
  standards_compliance:
    full_condition: standards_compliance_met
  vulnerability:
    min_condition: security_baseline_controls
    full_condition: security_multi_layer_with_adversarial_testing_and_audits
```

### quality_model.yaml
```yaml
version: 1
framework_source:
  maturity_levels: paper_table_1_ml_maturity_framework
  quality_requirements: genai_adaptation_docx

characteristics:
  utility:
    display_name: Utility
    description: Ability to provide useful, effective, and usable outcomes.
  economy:
    display_name: Economy
    description: Sustainability of cost-to-value and operational efficiency.
  robustness:
    display_name: Robustness
    description: Reliability under failures, changes, and scale.
  productionizability:
    display_name: Productionizability
    description: Operational readiness and repeatability in production.
  modifiability:
    display_name: Modifiability
    description: Ease and safety of changing the system over time.
  comprehensibility:
    display_name: Comprehensibility
    description: Clarity, discoverability, and traceability for humans.
  responsibility:
    display_name: Responsibility
    description: Trustworthiness, governance, and safety.

sub_characteristics:
  - id: accuracy
    display_name: Accuracy
    characteristic: utility
    minimal_requirement: Beats a baseline on a small golden set (minimum 50 examples) validated by domain experts.
    full_requirement: Beats a baseline on a comprehensive golden set (minimum 200 examples) with automated metrics and human evaluation.
    rationale: Sophisticated evaluation must capture factuality, relevance, task completion, and safety.

  - id: effectiveness
    display_name: Effectiveness
    characteristic: utility
    minimal_requirement: Effectiveness verified with an A/B experiment showing positive impact on business metrics.
    full_requirement: Effectiveness revalidated periodically and after major changes with no sustained degradation.
    rationale: Offline scores alone do not guarantee real-world impact.

  - id: responsiveness
    display_name: Responsiveness
    characteristic: utility
    minimal_requirement: "-"
    full_requirement: P95 and P99 latency targets are tracked and within acceptable bounds for the use case.
    rationale: Poor latency undermines adoption and user trust.

  - id: usability
    display_name: Usability
    characteristic: utility
    minimal_requirement: "-"
    full_requirement: System is deployed in an accessible serving infrastructure with appropriate user interfaces.
    rationale: Useful outputs must be reachable by intended users.

  - id: cost_effectiveness
    display_name: Cost-Effectiveness
    characteristic: economy
    minimal_requirement: System costs are comprehensively tracked and documented.
    full_requirement: Documented value generated exceeds total costs by a measurable margin.
    rationale: GenAI inference and retrieval costs can grow rapidly in production.

  - id: efficiency
    display_name: Efficiency
    characteristic: economy
    minimal_requirement: Basic operations are automated (evaluation runs, prompt updates, knowledge base refreshes).
    full_requirement: Prompts are token-efficient or model tuning/routing is optimized for cost-latency-performance tradeoffs.
    rationale: Small inefficiencies multiply quickly at high traffic.

  - id: availability
    display_name: Availability
    characteristic: robustness
    minimal_requirement: "-"
    full_requirement: Deployed service meets defined SLAs with fallback strategies.
    rationale: Downtime directly impacts business outcomes.

  - id: resilience
    display_name: Resilience
    characteristic: robustness
    minimal_requirement: Automated update pipelines have successful completion rate of at least 80% per quarter.
    full_requirement: Automated update pipeline success is at least 90% per quarter with rollback capability.
    rationale: Multi-component GenAI systems need safe failure handling.

  - id: adaptability
    display_name: Adaptability
    characteristic: robustness
    minimal_requirement: Documented manual process exists for updating system behavior.
    full_requirement: Automated mechanisms exist for behavior updates with user feedback integration.
    rationale: Static behavior degrades as users and knowledge evolve.

  - id: scalability
    display_name: Scalability
    characteristic: robustness
    minimal_requirement: "-"
    full_requirement: System dynamically scales resources based on traffic patterns with rate limiting and cost controls.
    rationale: Traffic spikes should not collapse quality or economics.

  - id: repeatability
    display_name: Repeatability
    characteristic: productionizability
    minimal_requirement: Prompt updates or fine-tuning processes are partially automated.
    full_requirement: Update processes (prompts, fine-tuning, evaluations) are fully automated and version controlled.
    rationale: Manual release loops are brittle and non-repeatable.

  - id: monitoring
    display_name: Monitoring
    characteristic: productionizability
    minimal_requirement: Basic operational metrics are monitored (latency, errors, throughput, tokens).
    full_requirement: Continuous automated evaluation is running on defined quality metrics.
    rationale: GenAI systems require continuous quality and cost visibility.

  - id: maintainability
    display_name: Maintainability
    characteristic: modifiability
    minimal_requirement: Prompts and code are versioned in source control.
    full_requirement: All key artifacts are versioned with change logs explaining rationale.
    rationale: Prompt and tool changes must be auditable and reversible.

  - id: modularity
    display_name: Modularity
    characteristic: modifiability
    minimal_requirement: Components are partially separated (prompt templates, retrieval, post-processing).
    full_requirement: Components are fully modular with clear interfaces.
    rationale: Modular boundaries reduce regression risk and speed iteration.

  - id: testability
    display_name: Testability
    characteristic: modifiability
    minimal_requirement: Source code has at least 50% test coverage.
    full_requirement: At least 80% test coverage including integration and adversarial cases.
    rationale: Reliable change velocity requires robust automated testing.

  - id: operability
    display_name: Operability
    characteristic: modifiability
    minimal_requirement: System is deployed with versioned releases and rollback capability.
    full_requirement: Progressive rollouts, safe rollback, and runtime kill switches are supported.
    rationale: Production incidents require fast, controlled recovery.

  - id: discoverability
    display_name: Discoverability
    characteristic: comprehensibility
    minimal_requirement: "-"
    full_requirement: System has a searchable registry entry with metadata and ownership.
    rationale: Discoverability prevents duplication and improves governance.

  - id: readability
    display_name: Readability
    characteristic: comprehensibility
    minimal_requirement: Prompts follow a consistent style guide.
    full_requirement: Prompts and source code follow unified style standards with clear structure.
    rationale: Readable artifacts reduce maintenance and onboarding cost.

  - id: traceability
    display_name: Traceability
    characteristic: comprehensibility
    minimal_requirement: Prompt versions and basic metadata are logged.
    full_requirement: End-to-end lineage is tracked across prompts, models, context, tools, and post-processing.
    rationale: Debugging and compliance require full execution lineage.

  - id: understandability
    display_name: Understandability
    characteristic: comprehensibility
    minimal_requirement: System has partial documentation covering basic functionality.
    full_requirement: Comprehensive architecture, limitations, runbooks, and onboarding documentation exist.
    rationale: Teams need shared understanding to operate safely at scale.

  - id: explainability
    display_name: Explainability
    characteristic: responsibility
    minimal_requirement: System provides basic reasoning or confidence signals where applicable.
    full_requirement: User-facing transparency mechanisms are implemented (citations, tool traces, confidence where relevant).
    rationale: Transparent behavior improves trust and oversight.

  - id: fairness
    display_name: Fairness
    characteristic: responsibility
    minimal_requirement: Basic fairness considerations are documented.
    full_requirement: Performance is evaluated across relevant groups with mitigation strategies for disparities.
    rationale: GenAI systems can amplify bias without explicit checks.

  - id: ownership
    display_name: Ownership
    characteristic: responsibility
    minimal_requirement: "-"
    full_requirement: A designated team is accountable for operating and maintaining the system.
    rationale: Ownership is required for incident response and long-term quality.

  - id: standards_compliance
    display_name: Standards Compliance
    characteristic: responsibility
    minimal_requirement: "-"
    full_requirement: Applicable legal, regulatory, and industry standards are met.
    rationale: Compliance constraints are mandatory, not optional.

  - id: vulnerability
    display_name: Vulnerability
    characteristic: responsibility
    minimal_requirement: Basic security controls are implemented.
    full_requirement: Multi-layer security controls are in place, including adversarial testing and regular audits.
    rationale: GenAI attack surfaces require layered defense.
```

### maturity_gates.csv
```csv
sub_characteristic,l1,l2,l3,l4,l5
accuracy,min,min,full,full,full
effectiveness,none,none,min,min,full
responsiveness,full,full,full,full,full
usability,none,none,full,full,full
cost_effectiveness,none,none,none,none,full
efficiency,none,none,none,min,full
availability,full,full,full,full,full
resilience,none,none,min,min,full
adaptability,none,none,min,full,full
scalability,none,none,none,none,full
repeatability,none,none,min,full,full
monitoring,none,none,min,min,full
maintainability,none,min,min,min,full
modularity,none,min,min,min,full
testability,none,min,min,min,full
operability,min,min,full,full,full
discoverability,none,none,full,full,full
readability,none,none,min,min,full
traceability,none,none,min,full,full
understandability,min,min,full,full,full
explainability,none,none,none,full,full
fairness,full,full,full,full,full
ownership,full,full,full,full,full
standards_compliance,full,full,full,full,full
vulnerability,full,full,full,full,full
```

### gap_scales.yaml
```yaml
gaps:
  "no": 0
  small: 1
  large: 2

fulfillment:
  full_met:
    - "no"
  min_met:
    - "no"
    - small
```

### recommendations.yaml
```yaml
recommendations:
  accuracy:
    min_action: Build a 50+ example expert-validated golden set and verify baseline outperformance.
    full_action: Expand to a 200+ example golden dataset with automated evals plus periodic human review.
  effectiveness:
    min_action: Run an A/B experiment tied to a primary business KPI and document results.
    full_action: Conduct periodic A/B experiments (block-out) where you test against the previous control group or a baseline.
  responsiveness:
    min_action: "-"
    full_action: Define and track P95/P99 latency continuously and enforce SLO compliance.
  usability:
    min_action: "-"
    full_action: Deploy a production-grade serving interface with explicit usability ownership.
  cost_effectiveness:
    min_action: Document and report all major cost components (API costs, storage, compute, human reviews, etc).
    full_action: Demonstrate sustained positive ROI and establish budget guardrails.
  efficiency:
    min_action: Automate basic operations such as evaluation, prompt release, and knowledge refresh workflows.
    full_action: Optimize prompts for token efficiency (in case of prompt based model) or fine-tuning for cost-latency-quality efficiency (in case of fine-tuned).
  availability:
    min_action: "-"
    full_action: Define and meet availability SLA targets with monitored fallback behavior.
  resilience:
    min_action: Raise automated pipeline (e.g., prompt updates, RAG index refresh, continuous evaluation) success rate to at least 80% per quarter.
    full_action: Raise automated pipeline success rate to at least 90%.
  adaptability:
    min_action: Document a repeatable process for behavior updates.
    full_action: Automate update loops using feedback and evaluation-gated releases.
  scalability:
    min_action: "-"
    full_action: Implement dynamic scaling with rate limiting and cost controls.
  repeatability:
    min_action: Partially automate prompt/model update pipelines.
    full_action: Fully automate update/evaluation flow with versioning.
  operability:
    min_action: Ensure versioned deployment and rollback.
    full_action: Add canary rollouts, safe rollback automation, and runtime kill switches.
  monitoring:
    min_action: Track core operational and token/cost metrics (e.g., response times, error rates, throughput, token usage).
    full_action: Add continuous automated output quality evaluation.
  maintainability:
    min_action: Version prompts and code in source control.
    full_action: Version all key artifacts with structured change rationale.
  modularity:
    min_action: Separate core components into modules, even partially.
    full_action: Fully enforce modularity across retrieval, prompting, generation, and safety components.
  testability:
    min_action: Reach at least 50% source code coverage.
    full_action: Reach at least 80% source code coverage with integration and adversarial tests.
  discoverability:
    min_action: "-"
    full_action: Register the system with searchable metadata (e.g., model details, prompts, example usage, limitations, ownership).
  readability:
    min_action: Apply a prompt style guide and structure conventions.
    full_action: Enforce unified readability standards for prompts and source code.
  traceability:
    min_action: Log prompt versions and core request metadata (e.g., timestamp, user ID, session ID, model version, model parameters).
    full_action: Capture end-to-end lineage across models, context, tool calls, reasoning traces and post-processing steps.
  understandability:
    min_action: Document core system information (e.g., system components, key modeling decision, evaluation results).
    full_action: Fully document the system's architecture (e.g., prompt engineering or finetunine rationale, known limitations, onboarding guides).
  explainability:
    min_action: Expose basic reasoning or confidence signals where applicable.
    full_action: Provide user-facing transparency artifacts (citations, tool traces, confidence).
  fairness:
    min_action: Document known fairness risks and assumptions.
    full_action: Evaluate across relevant demographic groups and implement mitigation for harmful disparities.
  ownership:
    min_action: "-"
    full_action: Assign a formally accountable team or individual as system owner with explicit responsibilities.
  standards_compliance:
    min_action: "-"
    full_action: Demonstrate compliance with required legal and industry standards.
  vulnerability:
    min_action: Implement baseline protections (input sanitization, secret handling, prompt injection checks).
    full_action: Add multi-layered security controls including bot detection, red teaming exercises, PII redaction, jailbreak defenses, and security audits.
```
