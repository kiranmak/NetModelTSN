from tsn_with_quota import run_tsn_simulation
from matplotlib import use

def test_gcl_absolute_schedule():
    # ---------------------------------------------------------
    # TEST 1: Absolute period allocations 
    # ---------------------------------------------------------
    gcl_absolute_profile = {
        "Control_TT":   {"period_us": 6000.0, "size_bytes": 200, "cyclic": True, "pri": 3},
        "Mission_Crit": {"period_us": 5000.0, "size_bytes": 400, "cyclic": True, "pri": 2},
        "Telemetry":    {"period_us": 4000.0, "size_bytes": 600, "cyclic": False, "pri": 1},
        "Best_Effort":  {"period_us": 2000.0, "size_bytes": 1200,"cyclic": False, "pri": 0},
    }
    
    sched_1 = [
        {"duration": 1000.0, "gate_state": 0b1000},
        {"duration": 2000.0, "gate_state": 0b1100},
        {"duration": 7000.0, "gate_state": 0b0111}
    ]
    run_tsn_simulation("opt_sched_10_20_70", sched_1, gcl_absolute_profile, sim_duration=100000.0)

    sched_2 = [
        {"duration": 3000.0, "gate_state": 0b1000},
        {"duration": 2000.0, "gate_state": 0b1100},
        {"duration": 5000.0, "gate_state": 0b0111}
    ]
    run_tsn_simulation("gen_shed_30_20_50", sched_2, gcl_absolute_profile, sim_duration=100000.0)


def test_quota_schedule():
    # ---------------------------------------------------------
    # TEST 2: Quota-based allocations (from tsn_with_quota.py)
    # ---------------------------------------------------------
    x = 0.006 + 0.004 + 0.002 + 0.048
    quota_profile_1 = {
        "Control_TT":   {"pct": 0.006, "size_bytes": 100, "cyclic": True, "pri": 3},  # Yields 6000.0 µs
        "Mission_Crit": {"pct": 0.004, "size_bytes": 400, "cyclic": True, "pri": 2},  # Yields 5000.0 µs
        "Telemetry":    {"pct": 0.002, "size_bytes": 600, "cyclic": False, "pri": 1}, # Yields 4000.0 µs
        "Best_Effort":  {"pct": 0.048, "size_bytes": 1200, "cyclic": False, "pri": 0},# Yields 2000.0 µs
        "idle":         {"pct": (1-x), "size_bytes": 0, "cyclic": False, "pri": 0}    # Safety room matches the gap
    }
    sched_2 = [
        {"duration": 2000.0, "gate_state": 0b1000},
        {"duration": 2000.0, "gate_state": 0b1100},
        {"duration": 6000.0, "gate_state": 0b0111}
    ]
    run_tsn_simulation("ct-10-mc-10-tm-40-be-10_sched_3_2_5", sched_2, quota_profile_1, sim_duration=50000.0)

    # ----------------------------------------------------------------------
    # FIX: Quota-based allocation that outputs identical period behaviors
    # ----------------------------------------------------------------------
    quota_profile_2 = {
        "Control_TT":   {"pct": 0.000266667, "size_bytes": 200, "cyclic": True, "pri": 3},  # Yields 6000.0 µs
        "Mission_Crit": {"pct": 0.00064,     "size_bytes": 400, "cyclic": True, "pri": 2},  # Yields 5000.0 µs
        "Telemetry":    {"pct": 0.0012,      "size_bytes": 600, "cyclic": False, "pri": 1}, # Yields 4000.0 µs
        "Best_Effort":  {"pct": 0.0048,      "size_bytes": 1200, "cyclic": False, "pri": 0},# Yields 2000.0 µs
        "idle":         {"pct": 0.993093333, "size_bytes": 0, "cyclic": False, "pri": 0}    # Safety room matches the gap
    }

    fast_gcl_schedule = [
        {"duration": 200.0, "gate_state": 0b1000},
        {"duration": 200.0, "gate_state": 0b1100},
        {"duration": 600.0, "gate_state": 0b0111}
    ]
    run_tsn_simulation("ct-20-mc-15-tm-10-be-30_sched_3", sched_2, quota_profile_2, sim_duration=50000.0)

def run_arrival_rate_tests():
    # Sched base definition used for the test run
    sched_baseline = [
        {"duration": 1000.0, "gate_state": 0b1000},
        {"duration": 2000.0, "gate_state": 0b1100},
        {"duration": 7000.0, "gate_state": 0b0111}
    ]

    # ------------------------------------------------------------------
    # NEW TEST 3: Configuring Traffic via Physical Transmission Rates (Hz)
    # ------------------------------------------------------------------
    hz_rate_profile = {
        "Control_TT":   {"rate_hz": 166.67, "size_bytes": 200, "cyclic": True, "pri": 3},  # ~6,000 µs
        "Mission_Crit": {"rate_hz": 200.0,  "size_bytes": 400, "cyclic": True, "pri": 2},  # ~5,000 µs
        "Telemetry":    {"rate_hz": 250.0,  "size_bytes": 600, "cyclic": False, "pri": 1}, # ~4000 µs
        "Best_Effort":  {"rate_hz": 500.0,  "size_bytes": 1200,"cyclic": False, "pri": 0}, # ~2000 µs
    }

    # We increase the simulation duration here to 1,000,000 µs (1 second)
    # to let these low-frequency physical rate samples build a meaningful trace.
    run_tsn_simulation("hz_rate_matching_profile", sched_baseline, hz_rate_profile, sim_duration=1_000_000.0)

if __name__ == "__main__":
    use('Agg')
    #test_gcl_absolute_schedule()
    test_quota_schedule()
