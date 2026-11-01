"""medai — shared imaging + model code used by both training scripts and the backend.

Keeping this in one package guarantees that the preprocessing applied at
inference time is byte-for-byte the same as the preprocessing used in training
(train/serve skew is one of the most common bugs in medical-imaging projects).
"""

__version__ = "0.1.0"

CLASSIFIER_LABELS = ["Lung Opacity"]  # one sigmoid output per label; RSNA Pneumonia task is binary
SEG_LABELS = ["background", "spleen"]  # MSD Task09_Spleen
