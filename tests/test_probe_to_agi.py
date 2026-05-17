"""
Smoke tests for probe_to_agi.

Network-free. Tests the dict-building logic against hand-built GPL198
table fixtures — does not call GEOparse. The fetch path (going to GEO
or reading from cache) is exercised implicitly whenever a notebook
calls probe_to_agi().
"""

import pandas as pd

from irilab2026.data import _build_probe_to_agi_dict


def _make_table(rows):
    """Build a tiny GPL198-shaped DataFrame from (ID, AGI) tuples."""
    return pd.DataFrame(rows, columns=['ID', 'AGI'])


def test_single_locus_probe_included():
    table = _make_table([('249264_s_at', 'AT5G42570')])
    result = _build_probe_to_agi_dict(table)
    assert result == {'249264_s_at': 'AT5G42570'}


def test_multi_locus_probe_gets_first_locus():
    table = _make_table([('254074_at', 'AT4G25490 /// AT4G25470')])
    result = _build_probe_to_agi_dict(table)
    assert result == {'254074_at': 'AT4G25490'}


def test_multi_locus_three_loci_gets_first():
    table = _make_table([
        ('245678_at', 'AT3G10000 /// AT3G10001 /// AT3G10002'),
    ])
    result = _build_probe_to_agi_dict(table)
    assert result == {'245678_at': 'AT3G10000'}


def test_nan_agi_is_dropped():
    table = _make_table([
        ('249264_s_at', 'AT5G42570'),
        ('AFFX-BioB-3_at', None),
    ])
    result = _build_probe_to_agi_dict(table)
    assert 'AFFX-BioB-3_at' not in result
    assert result == {'249264_s_at': 'AT5G42570'}


def test_empty_agi_string_is_dropped():
    table = _make_table([
        ('249264_s_at', 'AT5G42570'),
        ('design_stage_probe', ''),
    ])
    result = _build_probe_to_agi_dict(table)
    assert 'design_stage_probe' not in result


def test_agi_is_normalized_to_upper_case():
    table = _make_table([('249264_s_at', 'at5g42570')])
    result = _build_probe_to_agi_dict(table)
    assert result == {'249264_s_at': 'AT5G42570'}


def test_whitespace_around_agi_is_stripped():
    table = _make_table([('249264_s_at', '  AT5G42570  ')])
    result = _build_probe_to_agi_dict(table)
    assert result == {'249264_s_at': 'AT5G42570'}


def test_returns_dict_not_series():
    table = _make_table([('249264_s_at', 'AT5G42570')])
    result = _build_probe_to_agi_dict(table)
    assert isinstance(result, dict)


def test_mixed_table_handles_all_cases():
    """End-to-end sanity check with a representative mix."""
    table = _make_table([
        ('249264_s_at', 'AT5G42570'),                  # single-locus
        ('254074_at', 'AT4G25490 /// AT4G25470'),      # multi-locus
        ('AFFX-r2-Bs-dap-3_at', None),                 # control, no AGI
        ('245678_at', 'AT3G10000 /// AT3G10001'),      # multi-locus
        ('design_stage_probe', ''),                    # empty AGI
        ('254075_at', 'at4g25470'),                    # lower-case input
    ])
    result = _build_probe_to_agi_dict(table)
    assert result == {
        '249264_s_at': 'AT5G42570',
        '254074_at': 'AT4G25490',
        '245678_at': 'AT3G10000',
        '254075_at': 'AT4G25470',
    }