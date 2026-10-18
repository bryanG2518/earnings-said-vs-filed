"""Deterministic arithmetic. The only place numbers are created."""
from typing import Optional


def pct_change(new: float, old: float) -> Optional[float]:
    if old in (0, None) or new is None:
        return None
    return (new - old) / abs(old)


def midpoint(low: float, high: Optional[float] = None) -> float:
    return low if high is None else (low + high) / 2.0


def guidance_delta(prior_low, prior_high, actual_low, actual_high=None):
    """Compare a new figure (or new range) to a prior guidance range.

    Returns dict with direction ('above'|'within'|'below'|'raised'|'cut'|
    'held') and distance from the prior midpoint as a fraction.
    """
    prior_mid = midpoint(prior_low, prior_high)
    new_mid = midpoint(actual_low, actual_high)
    dist = pct_change(new_mid, prior_mid)
    is_range_update = actual_high is not None
    hi = prior_high if prior_high is not None else prior_low
    if is_range_update:
        if new_mid > prior_mid:
            direction = "raised"
        elif new_mid < prior_mid:
            direction = "cut"
        else:
            direction = "held"
    else:
        if actual_low > hi:
            direction = "above"
        elif actual_low < prior_low:
            direction = "below"
        else:
            direction = "within"
    return {"direction": direction, "distance": dist,
            "prior_mid": prior_mid, "new_mid": new_mid}


def one_time_share(gaap_eps: float, one_time_per_share: float) -> Optional[float]:
    if not gaap_eps:
        return None
    return one_time_per_share / abs(gaap_eps)


def divergence(a_now, a_prev, b_now, b_prev):
    """Growth gap between two related series (e.g. op income vs net income)."""
    ga, gb = pct_change(a_now, a_prev), pct_change(b_now, b_prev)
    if ga is None or gb is None:
        return None
    return {"growth_a": ga, "growth_b": gb, "gap": ga - gb}


def materiality(dollar_impact=None, revenue=None, eps_impact=None, eps=None,
                guidance_distance=None):
    """Materiality score in [0, 1]. Larger of revenue share, EPS share, or
    guidance distance. Returns None when nothing measurable was supplied."""
    parts = []
    if dollar_impact is not None and revenue:
        parts.append(abs(dollar_impact) / abs(revenue))
    if eps_impact is not None and eps:
        parts.append(abs(eps_impact) / abs(eps))
    if guidance_distance is not None:
        parts.append(abs(guidance_distance))
    if not parts:
        return None
    return min(1.0, max(parts))

FIXED_MIDDLE = 0.05   # score assigned to non-dollar findings
