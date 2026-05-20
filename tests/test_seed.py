"""Smoke tests for irilab2026.seed_all."""

import random

import numpy as np
import pytest
import torch

import irilab2026


def test_seed_all_torch_reproducible():
    """Calling seed_all(42) twice produces the same torch.rand sequence."""
    irilab2026.seed_all(42)
    a = torch.rand(5)

    irilab2026.seed_all(42)
    b = torch.rand(5)

    assert torch.equal(a, b), "torch RNG not reproducible after seed_all"


def test_seed_all_numpy_reproducible():
    """Calling seed_all(42) twice produces the same numpy random sequence."""
    irilab2026.seed_all(42)
    a = np.random.rand(5)

    irilab2026.seed_all(42)
    b = np.random.rand(5)

    assert np.array_equal(a, b), "numpy RNG not reproducible after seed_all"


def test_seed_all_python_reproducible():
    """Calling seed_all(42) twice produces the same random.random() sequence."""
    irilab2026.seed_all(42)
    a = [random.random() for _ in range(5)]

    irilab2026.seed_all(42)
    b = [random.random() for _ in range(5)]

    assert a == b, "Python random not reproducible after seed_all"


def test_seed_all_different_seeds_differ():
    """Different seeds give different sequences. Sanity check the seed argument
    actually does something."""
    irilab2026.seed_all(42)
    a = torch.rand(5)

    irilab2026.seed_all(123)
    b = torch.rand(5)

    assert not torch.equal(a, b), "Different seeds produced identical sequences"


def test_seed_all_sets_cudnn_deterministic():
    """seed_all should leave cudnn in deterministic mode."""
    irilab2026.seed_all(42)
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False


def test_seed_all_default_seed_is_42():
    """Calling seed_all() with no args uses 42 as the default."""
    irilab2026.seed_all()
    a = torch.rand(5)

    irilab2026.seed_all(42)
    b = torch.rand(5)

    assert torch.equal(a, b), "Default seed is not 42"