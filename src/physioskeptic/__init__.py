"""PhysioSkeptic: signal-quality-anchored skeptical reasoning for ECG/PPG rhythm diagnosis.

Public API surface:
  - PhysioPatchEncoder: dual-path encoder (paper §3.1)
  - build_patch_report: deterministic Patch Report generation (paper §3.2)
  - route_sample, challenge_count: SQI-gated routing (paper §3.3)
  - PhysioSkepticDebate: five-role debate orchestration (paper §3.3)
  - BaseLLMClient, MockLLMClient, OpenAICompatibleClient: LLM backends
"""
from physioskeptic.debate import PhysioSkepticDebate
from physioskeptic.encoder import PhysioPatchEncoder
from physioskeptic.llm_clients import BaseLLMClient, MockLLMClient, OpenAICompatibleClient
from physioskeptic.patch_report import PatchReport, build_patch_report
from physioskeptic.routing import Route, challenge_count, route_sample

__all__ = [
    "PhysioPatchEncoder",
    "build_patch_report",
    "PatchReport",
    "route_sample",
    "challenge_count",
    "Route",
    "PhysioSkepticDebate",
    "BaseLLMClient",
    "MockLLMClient",
    "OpenAICompatibleClient",
]
