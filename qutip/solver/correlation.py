__all__ = [
    'correlation_3op',
    'correlation_2op_1t', 'correlation_2op_2t', 'correlation_3op_1t',
    'correlation_3op_2t', 'coherence_function_g1', 'coherence_function_g2'
]

import numpy as np
import scipy.fftpack

from ..core import (
    qeye, Qobj, QobjEvo, liouvillian, spre, unstack_columns, stack_columns,
    tensor, qzero, expect
)
from .mesolve import MeSolver
from .mcsolve import McSolver
from .brmesolve import BRSolver
from .heom.bofin_solvers import HEOMSolver

from ..solve.steadystate import steadystate
from ..ui.progressbar import progess_bars

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

# low level correlation


def correlation_2op_1t(H, state0, taulist, c_ops, a_op, b_op,
                       solver="me", reverse=False, args={},
                       options={}):
    r"""
    Calculate the two-operator two-time correlation function:
    :math:`\left<A(t+\tau)B(t)\right>`
    along one time axis using the quantum regression theorem and the evolution
    solver indicated by the `solver` parameter.

    Parameters
    ----------

    H : Qobj, QobjEvo
        System Hamiltonian.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`. If 'state0' is 'None', then the steady state will
        be used as the initial state. The 'steady-state' is only implemented
        if ``c_ops`` are provided.
    taulist : array_like
        List of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    c_ops : list of {Qobj, QobjEvo}
        List of collapse operators
    a_op : Qobj, QobjEvo
        Operator A.
    b_op : Qobj, QobjEvo
        Operator B.
    reverse : bool {False, True}
        If `True`, calculate :math:`\left<A(t)B(t+\tau)\right>` instead of
        :math:`\left<A(t+\tau)B(t)\right>`.
    solver : str {'me', 'es'}
        Choice of solver, `me` for master-equation, and `es` for exponential
        series. `es` is equivalent to `me` with ``options={"method": "diag"}``.
    options : dict, optional
        Options for the solver. Only used with `me` solver.

    Returns
    -------
    corr_vec : ndarray
        An array of correlation values for the times specified by `taulist`.

    See Also
    --------
    :func:`correlation_3op` :
        Similar function supporting various solver types.

    References
    ----------
    See, Gardiner, Quantum Noise, Section 5.2.

    """
    solver = _make_solver(H, c_ops, args, options, solver)

    if reverse:
        A_op, B_op, C_op = a_op, b_op, 1
    else:
        A_op, B_op, C_op = 1, a_op, b_op
    if state0 is None:
        state0 = steadystate(H, c_ops)

    return correlation_3op(solver, state0, [0], taulist, A_op, B_op, C_op)[0]


def correlation_2op_2t(H, state0, tlist, taulist, c_ops, a_op, b_op,
                       solver="me", reverse=False, args={},
                       options={}):
    r"""
    Calculate the two-operator two-time correlation function:
    :math:`\left<A(t+\tau)B(t)\right>`
    along two time axes using the quantum regression theorem and the
    evolution solver indicated by the `solver` parameter.

    Parameters
    ----------
    H : Qobj, QobjEvo
        System Hamiltonian.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`. If 'state0' is 'None', then the steady state will
        be used as the initial state. The 'steady-state' is only implemented
        if ``c_ops`` are provided.
    tlist : array_like
        List of times for :math:`t`. tlist must be positive and contain the
        element `0`. When taking steady-steady correlations only one tlist
        value is necessary, i.e. when :math:`t \rightarrow \infty`; here
        tlist is automatically set, ignoring user input.
    taulist : array_like
        List of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    c_ops : list of {Qobj, QobjEvo}
        List of collapse operators
    a_op : Qobj, QobjEvo
        Operator A.
    b_op : Qobj, QobjEvo
        Operator B.
    reverse : bool {False, True}
        If `True`, calculate :math:`\left<A(t)B(t+\tau)\right>` instead of
        :math:`\left<A(t+\tau)B(t)\right>`.
    solver : str {'me', 'es'}
        Choice of solver, `me` for master-equation, and `es` for exponential
        series. `es` is equivalent to `me` with ``options={"method": "diag"}``.
    options : dict, optional
        Options for the solver. Only used with `me` solver.

    Returns
    -------
    corr_mat : ndarray
        An 2-dimensional array (matrix) of correlation values for the times
        specified by `tlist` (first index) and `taulist` (second index). If
        `tlist` is `None`, then a 1-dimensional array of correlation values
        is returned instead.

    See Also
    --------
    :func:`correlation_3op` :
        Similar function supporting various solver types.

    References
    ----------
    See, Gardiner, Quantum Noise, Section 5.2.

    """
    solver = _make_solver(H, c_ops, args, options, solver)
    if tlist is None:
        tlist = [0]
    if state0 is None:
        state0 = steadystate(H, c_ops)

    if reverse:
        A_op, B_op, C_op = a_op, b_op, 1
    else:
        A_op, B_op, C_op = 1, a_op, b_op

    return correlation_3op(solver, state0, tlist, taulist, A_op, B_op, C_op)


def correlation_3op_1t(H, state0, taulist, c_ops, a_op, b_op, c_op,
                       solver="me", args={},
                       options={}):
    r"""
    Calculate the three-operator two-time correlation function:
    :math:`\left<A(t)B(t+\tau)C(t)\right>` along one time axis using the
    quantum regression theorem and the evolution solver indicated by the
    `solver` parameter.

    Note: it is not possibly to calculate a physically meaningful correlation
    of this form where :math:`\tau<0`.

    Parameters
    ----------
    H : Qobj, QobjEvo
        System Hamiltonian.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`. If 'state0' is 'None', then the steady state will
        be used as the initial state. The 'steady-state' is only implemented
        if ``c_ops`` are provided.
    taulist : array_like
        List of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    c_ops : list of {Qobj, QobjEvo}
        List of collapse operators
    a_op : Qobj, QobjEvo
        Operator A.
    b_op : Qobj, QobjEvo
        Operator B.
    c_op : Qobj, QobjEvo
        Operator C.
    solver : str {'me', 'es'}
        Choice of solver, `me` for master-equation, and `es` for exponential
        series. `es` is equivalent to `me` with ``options={"method": "diag"}``.
    options : dict, optional
        Options for the solver. Only used with `me` solver.

    Returns
    -------
    corr_vec : array
        An array of correlation values for the times specified by `taulist`.

    See Also
    --------
    :func:`correlation_3op` :
        Similar function supporting various solver types.

    References
    ----------
    See, Gardiner, Quantum Noise, Section 5.2.

    """
    solver = _make_solver(H, c_ops, args, options, solver)
    if state0 is None:
        state0 = steadystate(H, c_ops)
    return correlation_3op(solver, state0, [0], taulist, a_op, b_op, c_op)[0]


def correlation_3op_2t(H, state0, tlist, taulist, c_ops, a_op, b_op, c_op,
                       solver="me", args={},
                       options={}):
    r"""
    Calculate the three-operator two-time correlation function:
    :math:`\left<A(t)B(t+\tau)C(t)\right>` along two time axes using the
    quantum regression theorem and the evolution solver indicated by the
    `solver` parameter.

    Note: it is not possibly to calculate a physically meaningful correlation
    of this form where :math:`\tau<0`.

    Parameters
    ----------
    H : Qobj, QobjEvo
        System Hamiltonian.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`. If 'state0' is 'None', then the steady state will
        be used as the initial state. The 'steady-state' is only implemented
        if ``c_ops`` are provided.
    tlist : array_like
        List of times for :math:`t`. tlist must be positive and contain the
        element `0`. When taking steady-steady correlations only one tlist
        value is necessary, i.e. when :math:`t \rightarrow \infty`; here
        tlist is automatically set, ignoring user input.
    taulist : array_like
        List of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    c_ops : list of {Qobj, QobjEvo}
        List of collapse operators
    a_op : Qobj, QobjEvo
        Operator A.
    b_op : Qobj, QobjEvo
        Operator B.
    c_op : Qobj, QobjEvo
        Operator C.
    solver : str {'me', 'es'}
        Choice of solver, `me` for master-equation, and `es` for exponential
        series. `es` is equivalent to `me` with ``options={"method": "diag"}``.
    options : dict, optional
        Options for the solver. Only used with `me` solver.

    Returns
    -------
    corr_mat : array
        An 2-dimensional array (matrix) of correlation values for the times
        specified by `tlist` (first index) and `taulist` (second index). If
        `tlist` is `None`, then a 1-dimensional array of correlation values
        is returned instead.

    See Also
    --------
    :func:`correlation_3op` :
        Similar function supporting various solver types.

    References
    ----------

    See, Gardiner, Quantum Noise, Section 5.2.

    """
    solver = _make_solver(H, c_ops, args, options, solver)

    if tlist is None:
        tlist = [0]
    if state0 is None:
        state0 = steadystate(H, c_ops)

    return correlation_3op(solver, state0, tlist, taulist, a_op, b_op, c_op)


# high level correlation

def coherence_function_g1(
    H, state0, taulist, c_ops, a_op, solver="me", args={}, options={}
):
    r"""
    Calculate the normalized first-order quantum coherence function:

    .. math::

        g^{(1)}(\tau) =
        \frac{\langle A^\dagger(\tau)A(0)\rangle}
        {\sqrt{\langle A^\dagger(\tau)A(\tau)\rangle
                \langle A^\dagger(0)A(0)\rangle}}

    using the quantum regression theorem and the evolution solver indicated by
    the `solver` parameter.

    Parameters
    ----------
    H : Qobj, QobjEvo
        System Hamiltonian.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`. If 'state0' is 'None', then the steady state will
        be used as the initial state. The 'steady-state' is only implemented
        if ``c_ops`` are provided.
    taulist : array_like
        list of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    c_ops : list of {Qobj, QobjEvo}
        List of collapse operators
    a_op : Qobj, QobjEvo
        Operator A.
    solver : str {'me', 'es'}
        Choice of solver, `me` for master-equation, and `es` for exponential
        series. `es` is equivalent to `me` with ``options={"method": "diag"}``.
    options : dict, optional
        Options for the solver. Only used with `me` solver.

    Returns
    -------
    g1, G1 : tuple
        The normalized and unnormalized second-order coherence function.

    """
    solver = _make_solver(H, c_ops, args, options, solver)

    # first calculate the photon number
    if state0 is None:
        state0 = steadystate(H, c_ops)
        n = np.array([expect(state0, a_op.dag() * a_op)])
    else:
        n = solver.run(state0, taulist, e_ops=[a_op.dag() * a_op]).expect[0]

    # calculate the correlation function G1 and normalize with n to obtain g1
    G1 = correlation_3op(solver, state0, [0], taulist, None, a_op.dag(), a_op)[0]

    g1 = G1 / np.sqrt(n[0] * np.array(n))[0]
    return g1, G1


def coherence_function_g2(H, state0, taulist, c_ops, a_op, solver="me",
                          args={}, options={}):
    r"""
    Calculate the normalized second-order quantum coherence function:

    .. math::

         g^{(2)}(\tau) =
        \frac{\langle A^\dagger(0)A^\dagger(\tau)A(\tau)A(0)\rangle}
        {\langle A^\dagger(\tau)A(\tau)\rangle
         \langle A^\dagger(0)A(0)\rangle}

    using the quantum regression theorem and the evolution solver indicated by
    the `solver` parameter.

    Parameters
    ----------
    H : Qobj
        system Hamiltonian, may be time-dependent for solver choice of `me`.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`. If 'state0' is 'None', then the steady state will
        be used as the initial state. The 'steady-state' is only implemented
        if ``c_ops`` are provided.
    taulist : array_like
        list of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    c_ops : list
        list of collapse operators, may be time-dependent for solver choice of
        `me`.
    a_op : Qobj
        operator A.
    args : dict
        Dictionary of arguments to be passed to solver.
    solver : str {'me', 'es'}
        Choice of solver, `me` for master-equation, and `es` for exponential
        series. `es` is equivalent to `me` with ``options={"method": "diag"}``.
    options : dict, optional
        Options for the solver. Only used with `me` solver.

    Returns
    -------
    g2, G2 : tuple
        The normalized and unnormalized second-order coherence function.

    """
    solver = _make_solver(H, c_ops, args, options, solver)

    # first calculate the photon number
    if state0 is None:
        state0 = steadystate(H, c_ops)
        n = np.array([expect(state0, a_op.dag() * a_op)])
    else:
        n = solver.run(state0, taulist, e_ops=[a_op.dag() * a_op]).expect[0]

    # calculate the correlation function G2 and normalize with n to obtain g2
    G2 = correlation_3op(solver, state0, [0], taulist,
                         a_op.dag(), a_op.dag() * a_op, a_op)[0]

    g2 = G2 / (n[0] * np.array(n))
    return g2, G2


def _make_solver(H, c_ops, args, options, solver):
    H = QobjEvo(H, args=args)
    c_ops = [QobjEvo(c_op, args=args) for c_op in c_ops]
    if solver == "me":
        solver_instance = MeSolver(H, c_ops, options=options)
    elif solver == "es":
        options = {"method": "diag"}
        solver_instance = MeSolver(H, c_ops, options=options)
    elif solver == "mc":
        raise ValueError("MC solver for correlation has been removed")
    return solver_instance


def correlation_3op(solver, state0, tlist, taulist, A=None, B=None, C=None):
    r"""
    Calculate the three-operator two-time correlation function:

        :math:`\left<A(t)B(t+\tau)C(t)\right>`.

    from a open system :class:`Solver`.

    Note: it is not possible to calculate a physically meaningful correlation
    where :math:`\tau<0`.

    Parameters
    ----------
    solver : :class:`MeSolver`, :class:`BRSolver`, :class:`HEOMSolver`
        Qutip solver for an open system.
    state0 : Qobj
        Initial state density matrix :math:`\rho(t_0)` or state vector
        :math:`\psi(t_0)`.
    tlist : array_like
        List of times for :math:`t`. tlist must be positive and contain the
        element `0`.
    taulist : array_like
        List of times for :math:`\tau`. taulist must be positive and contain
        the element `0`.
    A, B, C: Qobj, QobjEvo, optional, default=None
        Operators ``A``, ``B``, ``C`` from the equation ``<A(t)B(t+\tau)C(t)>``
        in the Schrodinger picture. They do not need to be all provided. For
        exemple, if ``A`` is not provided, ``<B(t+\tau)C(t)>`` is computed.

    Returns
    -------
    corr_mat : array
        An 2-dimensional array (matrix) of correlation values for the times
        specified by `tlist` (first index) and `taulist` (second index). If
        `tlist` is `None`, then a 1-dimensional array of correlation values
        is returned instead.
    """
    taulist = np.asarray(taulist)

    dims = state0.dims[0]
    A = QobjEvo(qeye(dims) if A in [None, 1] else A)
    B = QobjEvo(qeye(dims) if B in [None, 1] else B)
    C = QobjEvo(qeye(dims) if C in [None, 1] else C)

    if isinstance(solver, (MeSolver, BRSolver)):
        out = _correlation_3op_dm(solver, state0, tlist, taulist, A, B, C)
    elif isinstance(solver, McSolver):
        raise TypeError("Monte Carlo support for correlation was removed. "
                        "Please, tell us on GitHub issues if you need it!")
    elif isinstance(solver, HEOMSolver):
        raise TypeError("HEOM is not supported by correlation. "
                        "Please, tell us on GitHub issues if you need it!")
    else:
        raise TypeError("Only solvers able to evolve density matrices"
                        " are supported.")

    return out


def _correlation_3op_dm(solver, state0, tlist, taulist, A, B, C):
    old_opt = solver.options.copy()
    try:
        # We don't want to modify the solver
        # TODO: Solver could have a ``with`` or ``copy``.
        solver.options["normalize_output"] = False
        solver.options["progress_bar"] = False

        progress_bar = progess_bars[old_opt['progress_bar']]()
        progress_bar.start(len(taulist) + 1, **old_opt['progress_kwargs'])
        rho_t = solver.run(state0, tlist).states
        corr_mat = np.zeros([np.size(tlist), np.size(taulist)], dtype=complex)
        progress_bar.update()

        for t_idx, rho in enumerate(rho_t):
            t = tlist[t_idx]
            corr_mat[t_idx, :] = solver.run(
                C(t) @ rho @ A(t),
                taulist + t,
                e_ops=B
            ).expect[0]
            progress_bar.update()
        progress_bar.finished()

    finally:
        solver.options = old_opt

    return corr_mat