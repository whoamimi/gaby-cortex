---

title: AI Agent Architecture
nav_order: 2
description: AI/ML Dev Notes
collections:

---

- **Content**
{:toc}

Despite the hype surrounding “AI agents” and the pressure that accompanies the trend, they meaningfully extend the contemporary programming paradigm and, in doing so, expand what working programmers can reasonably build. While constructing the foundational—almost skeletal—codebase for my bots, I found myself reconsidering several design choices, especially in the following areas:

- Data system architecture. The realization that I’m not confined to the typical constraints of day-to-day data work—merely modeling or drafting how datasets are collected and stored—has been genuinely invigorating.
- The importance of logging and tracing. Put differently, they force me to quantify how far I push “decorative” functions and classes. There’s a fine line between adequate structure and over-engineering—and, more often than I’d like, I end up on the wrong side of it.

# **From User Event Driven Point-of-view**

The workflow is as follows:

```mermaid
sequenceDiagram
    autonumber
    actor User

    participant SC as SessionController
    participant LLM as GoogleGenAIProvider
    participant Cortex as AgentCortex
    participant DD as DataDiscovery
    participant Skel as SkeletonAgentPipeline
    participant Plan as Planner
    participant Exec as Executioner
    participant Eval as Evaluator

    User->>SC: new SessionController(dataset, **llm_kwargs)
    SC->>LLM: construct provider(**llm_kwargs)
    SC->>Cortex: construct AgentCortex()
    SC-->>User: controller ready

    User->>SC: execute_pipeline(**kwargs)

    loop for each stage in SessionController (e.g. discovery, modeller, transformer)
        SC->>DD: execute_pipeline(llm=LLM, skele=Skel, **kwargs)

        %% DataDiscovery first runs its own stages (e.g. Profiler),
        %% then delegates to the SkeletonAgentPipeline
        DD->>Skel: execute_pipeline(llm=LLM, objective=derived_objective, **kwargs)

        %% Planner
        Skel->>Plan: call (llm=LLM, objective)
        Plan-->>Skel: plannerResult (steps)

        %% Executioner (per step)
        loop for step in plannerResult.steps
            Skel->>Exec: call (llm=LLM, current_step=step)
            Exec-->>Skel: execResult
        end

        %% Evaluator
        Skel->>Eval: call (llm=LLM, results=all execResult)
        Eval-->>Skel: evaluationResult

        Skel-->>DD: skeletonTraces (planner, executor[], evaluator)
        DD-->>SC: stageState, skeletonTraces

        SC->>Cortex: agent.update(stageState, fieldPattern=stage_name)
    end

    SC-->>User: all traces and final state
```
