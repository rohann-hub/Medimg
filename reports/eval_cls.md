# Test-set evaluation — densenet121-rsna-202610301757

- N = 4003, prevalence = 22.5%
- AUROC = 0.881 (95% CI 0.869–0.892)
- ECE = 0.129
- At threshold 0.3056: sensitivity 0.888, specificity 0.6953, PPV 0.4588, NPV 0.9553
- Grad-CAM pointing game: 25.3% of 300 positives

## Subgroups

### sex

| group | n | prevalence | AUROC | sensitivity | specificity |
|---|---|---|---|---|---|
| F | 1670 | 0.223 | 0.8833 | 0.8952 | 0.7042 |
| M | 2333 | 0.227 | 0.8794 | 0.883 | 0.6889 |

### age_band

| group | n | prevalence | AUROC | sensitivity | specificity |
|---|---|---|---|---|---|
| <18 | 3944 | 0.224 | 0.8805 | 0.8856 | 0.6981 |

### view

| group | n | prevalence | AUROC | sensitivity | specificity |
|---|---|---|---|---|---|
| AP | 1824 | 0.387 | 0.8215 | 0.9376 | 0.4191 |
| PA | 2179 | 0.09 | 0.8689 | 0.7107 | 0.8512 |
