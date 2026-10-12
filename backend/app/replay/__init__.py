from .datasets import (
    CSVCounterfactualDataset,
    CounterfactualDataset,
    InMemoryCounterfactualDataset,
    NPZCounterfactualDataset,
    WAVCollectionCounterfactualDataset,
)


def __getattr__(name: str):
    # Bounded artifact readers are also used by low-level model/database code.
    # Loading them must not eagerly import the inference engine and its stack.
    if name == "AdaptiveReplayRunner":
        from .runner import AdaptiveReplayRunner
        return AdaptiveReplayRunner
    raise AttributeError(name)

__all__ = [
    "CounterfactualDataset", "InMemoryCounterfactualDataset", "NPZCounterfactualDataset",
    "CSVCounterfactualDataset", "WAVCollectionCounterfactualDataset",
    "AdaptiveReplayRunner",
]
