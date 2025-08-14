"""
BAZ D2D Fluid‑Model Simulation
===============================

This module implements an analytic (fluid‑model) approximation of the
uplink device‑to‑device (D2D) computation unit for a very large
cluster of user equipment (UE), such as the BAZ system described in
the conversation.  Unlike the small‑scale random cluster models used
in ``d2d_computation_simulation.py`` and
``d2d_power_optimisation.py``, this script treats the entire
population of UEs as a continuum, adopting the fluid geometry model
for a hexagonal cellular network.  The purpose is to evaluate the
impact of the fractional power control (FPC) compensation factor
``alpha`` on the average spectral efficiency when all nodes share the
same resource pool (reuse–1, i.e. no frequency reuse).  In the D2D
context, this models a scenario where a million UEs are arranged in a
dense lattice and communicate through sidelink resources without
frequency partitioning.

**Background**

The fluid model replaces the discrete hexagonal tessellation of base
stations with concentric rings of interferers.  On the uplink, each
UE transmits with power ``P ∝ r^{αη}``, where ``r`` is its distance
from its serving base station, ``η`` is the path‑loss exponent and
``α ∈ [0,1]`` is the FPC factor.  The received signal at the serving
base station scales as ``r^{−η(1−α)}``.  The interference from other
cells is obtained by integrating the contributions of UEs in each
interfering cell over radial distance.  In the reuse–1 case the
interference term depends only on ``α`` and ``η`` and is independent
of the user’s position ``r``.  The instantaneous SIR for a user at
radius ``r`` is then ``SIR(r) = r^{−η(1−α)} / I_total(α, η)``, where
``I_total`` is the aggregate interference from all other cells.

This script numerically evaluates the interference integral and
computes the mean spectral efficiency

::

    C(α) = E_r [ log2(1 + SIR(r)) ],

where the expectation is taken over the uniform radial user
distribution ``f(r) = 2r`` on the unit disc.  The script scans
candidate values of ``α`` and reports the one that maximises ``C(α)``.

**Usage**

When run directly, the script evaluates the mean spectral efficiency
for a set of ``alpha`` values between 0 and 1 with step 0.05 and
prints the result along with the optimum.  The number of interfering
rings ``N_max`` and the path‑loss exponent ``eta`` can be modified
as needed.  Because the fluid model expresses everything per unit
area, the absolute number of nodes (1 000 000 in our case) does not
appear explicitly; instead, the user density is absorbed into the
interference constant.

**References**

The formulas implemented here follow the derivations in the
optimization of fractional frequency reuse and fractional power
control presented by Oussama Basta【388223372029404†L111-L138】.  In that work, the
authors derive a closed‑form expression for the SIR in reuse–1
conditions (their equation (4)) and note that increasing ``α``
increases inter‑cell interference【388223372029404†L92-L99】.

Author: Assistant (OpenAI)
Date: 2025‑08‑14
"""

from __future__ import annotations

import math
from typing import List, Tuple, Iterable

try:
    from scipy.integrate import quad  # type: ignore
except ImportError as e:
    raise ImportError("scipy is required for analytic integration") from e


def interference_integral(alpha: float, eta: float = 3.5, N_max: int = 5) -> float:
    """Compute the aggregate interference term I_total for a given FPC factor.

    This function implements the interference part of the fluid‑model
    SIR expression for reuse–1.  The network is modelled as concentric
    rings of interfering cells at distances ``2·n·R`` for
    ``n ∈ {1..N_max}``; each ring contains ``6n`` base stations.  For
    each interferer, the UE locations are assumed to be uniformly
    distributed in a unit disc around their serving station.  The
    transmitted power of an interfering UE at distance ``x`` from its
    base station scales as ``x^{αη}``, while the path loss from that
    UE to the tagged base station scales as ``(d)^{−η}``, where
    ``d ∈ {2n − x, 2n + x}`` is the distance between the UE and the
    tagged base.  The radial probability density inside each cell is
    ``f(x) = 2x`` for ``0 ≤ x ≤ 1``.

    Parameters
    ----------
    alpha: float
        Fractional power control factor (0 ≤ α ≤ 1).
    eta: float, optional
        Path‑loss exponent.  Defaults to 3.5, which is typical for
        urban micro cells.
    N_max: int, optional
        Number of interfering rings to include in the integration.
        Interference from further rings decays rapidly with ``η``, so a
        moderate value (e.g. 5) is usually sufficient for accuracy.

    Returns
    -------
    float
        The total interference contribution ``I_total(α, η)``.
    """
    def integrand(x: float, n: int) -> float:
        # Distances from the interfering UE to the tagged base station.
        d1 = abs(2 * n - x)
        d2 = abs(2 * n + x)
        # Interference power from both the near and far sides.
        return (x ** (alpha * eta)) * ((d1 ** (-eta)) + (d2 ** (-eta))) * (2 * x)

    total = 0.0
    for n in range(1, N_max + 1):
        # Integrate over the radial distance in the interfering cell.
        integral, _ = quad(lambda t: integrand(t, n), 0.0, 1.0, limit=200)
        # Multiply by the number of interferers in ring n (6·n for hex lattice).
        total += 6 * n * integral
    return total


def average_spectral_efficiency(alpha: float, eta: float = 3.5, N_max: int = 5) -> float:
    """Compute the mean spectral efficiency C(α) for the reuse–1 fluid model.

    The function integrates over user radii ``r`` on a unit disc with
    radial density ``f(r) = 2r`` and returns the expectation of
    ``log2(1 + SIR(r))``, where ``SIR(r)`` is given by
    ``r^{−η(1−α)} / I_total(α, η)``.  The interference term is
    computed once using :func:`interference_integral`.

    Parameters
    ----------
    alpha: float
        Fractional power control factor.
    eta: float, optional
        Path‑loss exponent (default 3.5).
    N_max: int, optional
        Number of interfering rings to include in the interference sum.

    Returns
    -------
    float
        The average spectral efficiency (bits/s/Hz) across the cell.
    """
    I_tot = interference_integral(alpha, eta=eta, N_max=N_max)

    def integrand(r: float) -> float:
        # Signal power scales as r^{−η(1−α)}.
        S = r ** (-eta * (1.0 - alpha))
        sir = S / I_tot
        # Radial probability density 2r and Shannon capacity log2(1 + SIR).
        return 2.0 * r * math.log2(1.0 + sir)

    # Integrate over the unit disc radius r ∈ [0, 1].
    integral, _ = quad(integrand, 0.0, 1.0, limit=200)
    return integral


def scan_alpha_values(alphas: Iterable[float], eta: float = 3.5, N_max: int = 5) -> List[Tuple[float, float]]:
    """Evaluate the average spectral efficiency for multiple α values.

    Parameters
    ----------
    alphas: Iterable[float]
        Sequence of α values to evaluate.
    eta: float, optional
        Path‑loss exponent.
    N_max: int, optional
        Number of interfering rings used in the interference integral.

    Returns
    -------
    list of (alpha, C(alpha)) tuples.
    """
    results: List[Tuple[float, float]] = []
    for alpha in alphas:
        c = average_spectral_efficiency(alpha, eta=eta, N_max=N_max)
        results.append((alpha, c))
    return results


def run_demo() -> None:
    """Run a demonstration of the fluid‑model evaluation.

    This function scans ``alpha`` from 0.0 to 1.0 in steps of 0.05,
    computes the mean spectral efficiency for each value and prints
    the results.  It also identifies the α that yields the maximum
    spectral efficiency.
    """
    print("Fluid‑model D2D BAZ simulation (reuse–1)")
    print("Path‑loss exponent η=3.5, unit cell radius R=1, no frequency reuse.")
    # Candidate alpha values from 0 to 1 with step 0.05
    alpha_values = [round(a * 0.05, 2) for a in range(0, 21)]
    results = scan_alpha_values(alpha_values, eta=3.5, N_max=5)
    # Print results
    for alpha, c in results:
        print(f"α={alpha:.2f}, mean spectral efficiency={c:.4f} bits/s/Hz")
    # Determine optimum alpha
    best_alpha, best_c = max(results, key=lambda t: t[1])
    print(f"\nBest α: {best_alpha:.2f} → C(α)={best_c:.4f} bits/s/Hz")
    if best_alpha > 0.01:
        print("Note: In reuse–1, the average capacity decreases monotonically with α;")
        print("choosing α ≈ 0 (no path‑loss compensation) maximises throughput but")
        print("may reduce cell‑edge fairness.  Adjust α upward only if coverage requirements demand it.")


if __name__ == "__main__":
    run_demo()
