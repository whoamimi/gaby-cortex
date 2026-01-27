---

title: AI Agent Architecture
nav_order: 1
description: AI/ML Dev Notes

---

- **Content**
{:toc}

Despite the hyped nature of 'AI Agent' usage in this generation and the pressure that it brings, it extends the current programming paradigm and to current programmers. Whilst building the fundamental or skeletal codebase for my bots, it prompted me to reconsider many designs specific to the following areas:

- Data system Architectures. The idea that I am not limited to modelling or drafting the format of how these dataset is collected or stored - like in most day-to-day jobs of a data worker, brought me alot of joy.
- Importance of Logging and traces. In other words, measuring the intensity of my abuse on using decorative functions and classes. There is a fine line between sufficient and over-engineer and unfortunately, I often find myself in the latter more than I intend to.

# **How the module works**

## **Building an Agent**

All AI Agents are built by inheriting `AgentBasement` Object class.

## **Pipelines**

All Pipelines and workflows are built by inheriting `AgentPipeline` which inherits `OrderedDict`. The inheritance between 


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
