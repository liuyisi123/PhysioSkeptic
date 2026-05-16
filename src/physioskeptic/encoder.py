"""PhysioPatch encoder: dual-path ECG/PPG encoder with SQI-gated fusion.

Architecture overview (paper §3.1):
  Path A — temporal:   beat patches → MultiScaleTokenizer (4-kernel 1D-CNN)
                       → 6-layer Transformer → H_temp ∈ R^{N×d}
  Path B — frequency:  STFT spectrogram → 2D-CNN → h_freq ∈ R^{128}
  SQI head:            q̂ = σ(MLP(mean(H_temp)))           [Eq. (2)]
  Fusion:              H_fused = q̂·H_temp + (1-q̂)·1_N (h_freq W_f)^T  [Eq. (3)]
  Cross-modal:         Q-Former projector with 32 learned queries

Pre-training losses (paper §3.2):
  L = L_reconstruct + 0.5·L_InfoNCE + 0.1·L_SQI
  τ_contrastive = 0.07, queue = 4096
  AdamW (β1=0.9, β2=0.999, wd=1e-4), cosine LR, 10K warmup, peak lr=3e-4,
  200K steps, batch 512, 8×A100 80 GB.
"""
from __future__ import annotations

from dataclasses import dataclass
import torch
from torch import nn


@dataclass
class EncoderOutput:
    """Outputs returned by PhysioPatchEncoder.forward.

    Attributes:
        tokens: Fused beat tokens H_fused ∈ R^{B×N×d} after SQI-gated fusion (Eq. 3).
        q_hat: Scalar SQI estimate q̂ ∈ [0, 1] per sample in the batch (Eq. 2).
        freq_embedding: Frequency embedding h_freq ∈ R^{B×freq_dim} from Path B.
        cross_modal_tokens: Cross-modal tokens from Q-Former projector, shape (B, 32, d).
        attention: Optional transformer attention weights, shape (B, N, N) or None.
    """

    tokens: torch.Tensor
    q_hat: torch.Tensor
    freq_embedding: torch.Tensor
    cross_modal_tokens: torch.Tensor | None = None
    attention: torch.Tensor | None = None


class MultiScaleTokenizer(nn.Module):
    """Multi-scale 1D-CNN tokenizer for beat patches (Path A, paper §3.1).

    Applies parallel 1D convolutions with four kernel sizes, concatenates their
    mean-pooled feature maps, and projects to d_model. This captures morphological
    features at multiple temporal resolutions.

    Args:
        d_model: Output feature dimension (must be divisible by len(kernels)).
        kernels: Tuple of kernel sizes for the parallel branches.
    """

    def __init__(self, d_model: int = 256, kernels: tuple[int, ...] = (5, 13, 25, 51)) -> None:
        super().__init__()
        channels = d_model // len(kernels)
        self.branches = nn.ModuleList(
            [nn.Conv1d(1, channels, kernel_size=k, padding=k // 2) for k in kernels]
        )
        self.proj = nn.Linear(channels * len(kernels), d_model)

    def forward(self, patches: torch.Tensor) -> torch.Tensor:
        """Tokenize a batch of beat patches.

        Args:
            patches: Beat patches of shape (B, N, L) — B samples, N beats, L samples.

        Returns:
            Token embeddings of shape (B, N, d_model).
        """
        b, n, l = patches.shape
        x = patches.reshape(b * n, 1, l)
        feats = [torch.relu(conv(x)).mean(dim=-1) for conv in self.branches]
        y = torch.cat(feats, dim=-1).reshape(b, n, -1)
        return self.proj(y)


class FrequencyEncoder(nn.Module):
    """2D-CNN encoder for STFT spectrograms (Path B, paper §3.1).

    Processes spectrograms computed with W=256, H=64, N_FFT=512, filtered to
    0.5–30 Hz. Outputs a fixed-length frequency embedding h_freq ∈ R^{out_dim}.

    Args:
        out_dim: Dimension of the output frequency embedding (default 128).
    """

    def __init__(self, out_dim: int = 128) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(), nn.Linear(32, out_dim), nn.ReLU()
        )

    def forward(self, spectrogram: torch.Tensor) -> torch.Tensor:
        """Encode a batch of spectrograms.

        Args:
            spectrogram: Magnitude spectrogram of shape (B, F, T).

        Returns:
            Frequency embeddings h_freq of shape (B, out_dim).
        """
        return self.net(spectrogram.unsqueeze(1))


class QFormerProjector(nn.Module):
    """Q-Former cross-modal projector with 32 learned queries (paper §3.1).

    Adapts BLIP-2 Q-Former design: a fixed set of learned query vectors cross-attend
    to the fused beat token sequence H_fused to distill a compact cross-modal
    representation for LLM conditioning.

    Args:
        n_queries: Number of learned query vectors (default 32, per paper).
        d_model: Token and query feature dimension.
        nhead: Number of attention heads.
    """

    def __init__(self, n_queries: int = 32, d_model: int = 256, nhead: int = 8) -> None:
        super().__init__()
        self.queries = nn.Parameter(torch.zeros(1, n_queries, d_model))
        nn.init.trunc_normal_(self.queries, std=0.02)
        self.cross_attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, h_fused: torch.Tensor) -> torch.Tensor:
        """Apply Q-Former cross-attention over fused beat tokens.

        Args:
            h_fused: Fused beat tokens H_fused of shape (B, N, d_model).

        Returns:
            Cross-modal token sequence of shape (B, n_queries, d_model).
        """
        q = self.queries.expand(h_fused.size(0), -1, -1)
        out, _ = self.cross_attn(q, h_fused, h_fused)
        return self.norm(out)


class PhysioPatchEncoder(nn.Module):
    """Full PhysioPatch encoder combining Path A (temporal) and Path B (frequency).

    Implements the dual-path architecture from paper §3.1:
      - Path A: MultiScaleTokenizer → 6-layer Transformer → H_temp (Eq. 1)
      - Path B: FrequencyEncoder → h_freq
      - SQI head: q̂ = σ(MLP(mean(H_temp)))  (Eq. 2)
      - Fusion: H_fused = q̂·H_temp + (1-q̂)·1_N(h_freq W_f)^T  (Eq. 3),
                where W_f ∈ R^{freq_dim×d_model}
      - Cross-modal projector: Q-Former with 32 learned queries

    Args:
        d_model: Transformer hidden dimension d (default 256).
        freq_dim: Frequency embedding dimension (default 128, = dim of h_freq).
        layers: Number of Transformer encoder layers (default 6, per paper).
        n_queries: Number of Q-Former learned queries (default 32, per paper).
    """

    def __init__(
        self,
        d_model: int = 256,
        freq_dim: int = 128,
        layers: int = 6,
        n_queries: int = 32,
    ) -> None:
        super().__init__()
        self.tokenizer = MultiScaleTokenizer(d_model=d_model)
        enc_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=8, batch_first=True)
        self.temporal = nn.TransformerEncoder(enc_layer, num_layers=layers)
        # SQI head: σ(MLP(mean(H_temp))) → q̂ ∈ [0, 1]  (Eq. 2)
        self.sqi_head = nn.Sequential(nn.LayerNorm(d_model), nn.Linear(d_model, 1), nn.Sigmoid())
        self.freq_encoder = FrequencyEncoder(freq_dim)
        # W_f ∈ R^{freq_dim × d_model} — projects h_freq into token space for Eq. (3)
        self.W_f = nn.Linear(freq_dim, d_model)
        self.qformer = QFormerProjector(n_queries=n_queries, d_model=d_model)

    def forward(self, patches: torch.Tensor, spectrogram: torch.Tensor) -> EncoderOutput:
        """Encode beat patches and spectrogram into fused beat tokens.

        Args:
            patches: Beat-aligned patches of shape (B, N, L).
            spectrogram: STFT magnitude spectrogram of shape (B, F, T),
                         computed with W=256, H=64, N_FFT=512, range 0.5–30 Hz.

        Returns:
            EncoderOutput with fused tokens, q̂, h_freq, and cross-modal tokens.
        """
        # Path A: temporal morphology (Eq. 1)
        h_temp = self.temporal(self.tokenizer(patches))  # (B, N, d)

        # SQI head: q̂ = σ(MLP(mean(H_temp)))  (Eq. 2)
        q_hat = self.sqi_head(h_temp.mean(dim=1)).squeeze(-1)  # (B,)

        # Path B: frequency-domain rhythm structure
        h_freq = self.freq_encoder(spectrogram)  # (B, freq_dim)

        # Eq. (3): H_fused = q̂·H_temp + (1-q̂)·1_N (h_freq W_f)^T
        # W_f projects h_freq → (B, d); broadcast over N beats via unsqueeze
        freq_tok = self.W_f(h_freq).unsqueeze(1)  # (B, 1, d) — equivalent to 1_N (h_freq W_f)^T
        h_fused = q_hat[:, None, None] * h_temp + (1.0 - q_hat[:, None, None]) * freq_tok

        # Cross-modal projector: 32 learned Q-Former queries
        cross_modal = self.qformer(h_fused)  # (B, 32, d)

        return EncoderOutput(
            tokens=h_fused,
            q_hat=q_hat,
            freq_embedding=h_freq,
            cross_modal_tokens=cross_modal,
        )
