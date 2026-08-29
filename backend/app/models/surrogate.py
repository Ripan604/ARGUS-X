from __future__ import annotations

import torch
from torch import nn


class ForwardSurrogate(nn.Module):
    """Compact learned digital-twin surrogate for signal feature prediction."""

    def __init__(self, input_size: int, output_size: int, hidden_size: int = 96) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.SiLU(),
            nn.LayerNorm(hidden_size),
            nn.Linear(hidden_size, hidden_size),
            nn.SiLU(),
            nn.Linear(hidden_size, output_size),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.network(values)
