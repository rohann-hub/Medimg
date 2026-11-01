"""Model factories + checkpoint format.

A checkpoint is a dict saved with torch.save:
    {
      "state_dict": ...,
      "meta": {"arch", "task", "labels", "image_size", "threshold",
               "model_version", "trained_on", "metrics", ...}
    }
Embedding metadata means the backend never has to guess how a model was built,
and every prediction can be traced to an exact model version in the audit log.
"""
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn

CLASSIFIER_ARCHS = ("densenet121", "efficientnet_b0", "efficientnet_b3")


def build_classifier(arch: str = "densenet121", num_classes: int = 1, pretrained: bool = True) -> nn.Module:
    """Transfer learning: ImageNet backbone + fresh head.

    num_classes=1 → single sigmoid output (binary task, BCEWithLogitsLoss).
    For multi-label tasks like CheXpert/NIH-14, set num_classes=14 and keep sigmoid.
    """
    import torchvision.models as tvm

    if arch == "densenet121":
        m = tvm.densenet121(weights=tvm.DenseNet121_Weights.IMAGENET1K_V1 if pretrained else None)
        m.classifier = nn.Linear(m.classifier.in_features, num_classes)
    elif arch.startswith("efficientnet_"):
        ctor = getattr(tvm, arch)
        weights = getattr(tvm, f"EfficientNet_{arch.split('_')[1].upper()}_Weights").IMAGENET1K_V1 if pretrained else None
        m = ctor(weights=weights)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, num_classes)
    else:
        raise ValueError(f"unknown arch {arch!r}; choose from {CLASSIFIER_ARCHS}")
    return m


def gradcam_target_layer(model: nn.Module, arch: str) -> nn.Module:
    """Last convolutional block — highest-level features that still have spatial layout."""
    if arch == "densenet121":
        return model.features.denseblock4  # type: ignore[attr-defined]
    if arch.startswith("efficientnet_"):
        return model.features[-1]  # type: ignore[attr-defined,index]
    raise ValueError(arch)


def build_unet3d(out_channels: int = 2) -> nn.Module:
    """3D U-Net (MONAI) with residual units — the standard MONAI spleen-tutorial config."""
    from monai.networks.layers import Norm
    from monai.networks.nets import UNet

    return UNet(
        spatial_dims=3,
        in_channels=1,
        out_channels=out_channels,
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2),
        num_res_units=2,
        norm=Norm.BATCH,
    )


def save_checkpoint(path: str | Path, model: nn.Module, meta: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "meta": meta}, path)


def load_checkpoint(path: str | Path, map_location: str = "cpu") -> tuple[nn.Module, dict]:
    ckpt = torch.load(str(path), map_location=map_location, weights_only=False)
    meta = ckpt["meta"]
    if meta["task"] == "classification":
        model = build_classifier(meta["arch"], num_classes=len(meta["labels"]), pretrained=False)
    elif meta["task"] == "segmentation":
        model = build_unet3d(out_channels=len(meta["labels"]))
    else:
        raise ValueError(meta["task"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, meta
