"""Grad-CAM (Selvaraju et al., 2017), implemented from scratch so you can explain every line in a viva.

Idea: take the feature maps A_k of the last conv block and the gradient of the
class score y_c w.r.t. them. Average the gradient spatially to get one weight
per channel (how much that channel matters for class c), take the weighted sum
of feature maps, ReLU it (keep only evidence *for* the class), upsample to the
input size.

    alpha_k = mean_{i,j} dy_c / dA_k[i,j]
    CAM     = ReLU( sum_k alpha_k * A_k )

Caveat to write in your report: Grad-CAM shows where the model looked, not
*why*, and it is coarse (DenseNet121 at 320px → 10x10 map). It can highlight
shortcuts such as text markers or tubes. That is a feature for auditing, not a
localisation tool.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GradCAM:
    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self._h1 = target_layer.register_forward_hook(self._save_act)
        self._h2 = target_layer.register_full_backward_hook(self._save_grad)

    def _save_act(self, _m, _inp, out):
        self.activations = out.detach()

    def _save_grad(self, _m, _gin, gout):
        self.gradients = gout[0].detach()

    def remove(self) -> None:
        self._h1.remove()
        self._h2.remove()

    def __call__(self, x: torch.Tensor, class_idx: int = 0) -> tuple[np.ndarray, torch.Tensor]:
        """x: (1,C,H,W). Returns (cam HxW in [0,1], raw logits)."""
        self.model.eval()
        x = x.clone().requires_grad_(True)  # needed so backward hooks fire even with frozen params
        self.model.zero_grad(set_to_none=True)
        logits = self.model(x)
        logits[0, class_idx].backward()
        assert self.activations is not None and self.gradients is not None
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)  # (1,K,1,1)
        cam = F.relu((weights * self.activations).sum(dim=1, keepdim=True))  # (1,1,h,w)
        cam = F.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0]
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        return cam.cpu().numpy().astype(np.float32), logits.detach()
