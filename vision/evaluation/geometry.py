"""Pixel geometry and one-to-one matching. Numerical dependencies are optional."""


def clip_box(box, width, height):
    return [
        max(0.0, min(float(v), limit))
        for v, limit in zip(box, (width, height, width, height), strict=True)
    ]


def area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def intersection(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def iou(a, b):
    overlap = intersection(a, b)
    union = area(a) + area(b) - overlap
    return overlap / union if union > 0 else 0.0


def prediction_ioa(prediction, ignored):
    size = area(prediction)
    return intersection(prediction, ignored) / size if size > 0 else 0.0


def prepare_predictions(people, predictions, config):
    """Keep every prediction eligible for real truth, even if it also overlaps ignores."""
    valid = [p for p in people if not p.ignore]
    ignored = [p for p in people if p.ignore]
    kept, excluded = [], []
    for prediction in predictions:
        eligible = any(iou(p.xyxy, prediction["xyxy"]) >= config.match_iou for p in valid)
        covered = any(
            prediction_ioa(prediction["xyxy"], p.xyxy) >= config.ignore_ioa for p in ignored
        )
        (excluded if covered and not eligible else kept).append(prediction)
    return valid, ignored, kept, excluded


def iou_matrix(people, predictions):
    import numpy as np

    return np.asarray(
        [[iou(p.xyxy, d["xyxy"]) for d in predictions] for p in people], dtype=float
    ).reshape(len(people), len(predictions))


def match_detection(matrix, threshold):
    """Maximize eligible pair count before IoU sum; invalid pairs never consume truth."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    if not matrix.size:
        return []
    # A lost match costs more than the maximum possible total IoU gain. Unlike
    # plain sum-IoU assignment, this cannot trade two weak TPs for one strong TP.
    eligible = matrix >= threshold
    bonus = min(matrix.shape) + 1
    weights = np.where(eligible, bonus + matrix, 0.0)
    rows, columns = linear_sum_assignment(-weights)
    return [(int(r), int(c)) for r, c in zip(rows, columns, strict=True) if eligible[r, c]]
