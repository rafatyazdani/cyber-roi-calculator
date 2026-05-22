import math


def calculate_ale(asset_value, threat_frequency, vulnerability_score):
    """
    Calculate the baseline Annual Loss Expectancy (ALE) before any control is applied.

    Inputs:
        asset_value (float): Monetary value of the asset at risk.
        threat_frequency (float): Expected number of threat events per year (ARO).
        vulnerability_score (float): Likelihood the threat succeeds, in [0, 1].

    Output:
        float: Baseline ALE = asset_value * threat_frequency * vulnerability_score.
    """
    return asset_value * threat_frequency * vulnerability_score


def calculate_residual_ale(ale, reduction_pct):
    """
    Apply a control's risk reduction to the baseline ALE.

    Inputs:
        ale (float): Baseline Annual Loss Expectancy.
        reduction_pct (float): Risk reduction provided by the control, in [0, 1]
            (e.g. 0.60 for an MFA control that reduces ALE by 60%).

    Output:
        float: Residual ALE = ale * (1 - reduction_pct).
    """
    return ale * (1 - reduction_pct)


def effective_reduction(reduction_pct, year, decay_rate=0.08):
    """
    Compute a control's effective risk reduction at a given year, accounting for decay.

    Inputs:
        reduction_pct (float): Initial risk reduction, in [0, 1].
        year (int | float): Years since the control was deployed (year 1 = first year).
        decay_rate (float): Continuous annual decay rate. Default 0.08 (8% per year).

    Output:
        float: Effective reduction = reduction_pct * exp(-decay_rate * year).
    """
    return reduction_pct * math.exp(-decay_rate * year)


def annual_ale_reductions(ale, reduction_pct, years=5, decay_rate=0.08):
    """
    Project the dollar value of ALE reduction for each year over a horizon, with decay.

    Inputs:
        ale (float): Baseline Annual Loss Expectancy.
        reduction_pct (float): Initial risk reduction, in [0, 1].
        years (int): Number of years in the horizon. Default 5.
        decay_rate (float): Continuous annual decay rate. Default 0.08.

    Output:
        list[float]: ALE reduction per year, length `years`,
            where entry i = ale * effective_reduction(reduction_pct, i+1, decay_rate).
    """
    return [
        ale * effective_reduction(reduction_pct, year, decay_rate)
        for year in range(1, years + 1)
    ]


def annual_costs(annual_cost, years=5):
    """
    Expand a flat annual control cost into a per-year cost series.

    Inputs:
        annual_cost (float): Cost to operate the control for one year.
        years (int): Number of years in the horizon. Default 5.

    Output:
        list[float]: Cost per year, length `years`.
    """
    return [annual_cost] * years


def calculate_roi(ale_reductions, costs):
    """
    Calculate ROI as a percentage over the horizon.

    Inputs:
        ale_reductions (list[float]): ALE reduction per year.
        costs (list[float]): Control cost per year.

    Output:
        float: ROI percentage =
            (sum(ale_reductions) - sum(costs)) / sum(costs) * 100.
            Returns float('inf') if total cost is 0 and there is any benefit,
            or 0.0 if both totals are 0.
    """
    total_reduction = sum(ale_reductions)
    total_cost = sum(costs)
    if total_cost == 0:
        return 0.0 if total_reduction == 0 else float("inf")
    return (total_reduction - total_cost) / total_cost * 100


def calculate_payback_period(ale_reductions, costs):
    """
    Find the year at which cumulative ALE reduction first exceeds cumulative cost.

    Inputs:
        ale_reductions (list[float]): ALE reduction per year.
        costs (list[float]): Control cost per year.

    Output:
        int | None: 1-indexed year of payback, or None if payback is not reached
            within the provided horizon.
    """
    cumulative_reduction = 0.0
    cumulative_cost = 0.0
    for year, (reduction, cost) in enumerate(zip(ale_reductions, costs), start=1):
        cumulative_reduction += reduction
        cumulative_cost += cost
        if cumulative_reduction > cumulative_cost:
            return year
    return None
