import simpy
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import use
from tsn_switch import TsnSwitch

# ==========================================
# 1. UPGRADED TSN SIMULATION ENGINE
# ==========================================

def configure_tsn_traffic_periods(allocations, link_speed_gbps=1.0):
    """
    Computes required period_us for traffic classes supporting:
    - Fixed intervals ('period_us')
    - Physical rates ('rate_hz')
    - Bandwidth quotas ('pct')
    """
    link_speed_bits_per_us = link_speed_gbps * 1000.0

    # Calculate percentage totals *only* for the elements explicitly using quota allocations
    total_pct = sum(config.get("pct", 0) for config in allocations.values() if "pct" in config)
    if total_pct > 0 and not np.isclose(total_pct, 1.0) and any("pct" in c for c in allocations.values() if c != "idle"):
        raise ValueError(f"Total budget allocations must equal 100% (1.0). Currently: {total_pct*100}%")

    computed_periods = {}
    print("\n--- TSN Traffic Profile Configuration ---")
    for traffic_class, config in allocations.items():
        if traffic_class == "idle":
            continue

        # Option A: User specified a direct frequency in Hz
        if "rate_hz" in config:
            rate_hz = config["rate_hz"]
            period_us = 1_000_000.0 / rate_hz
            computed_periods[traffic_class] = period_us

            # Compute tracking metrics to print implied link load
            implied_bits_per_us = (config["size_bytes"] * 8) / period_us
            implied_pct = (implied_bits_per_us / link_speed_bits_per_us) * 100
            print(f"Class: {traffic_class:<15} | Size: {config['size_bytes']:>4} Bytes | "
                  f"Rate: {rate_hz:>6.1f} Hz  | Computed period_us: {period_us:>8.2f} µs (Load: {implied_pct:.4f}%)")

        # Option B: User specified a fixed interval period directly
        elif "period_us" in config:
            period_us = config["period_us"]
            implied_bits_per_us = (config["size_bytes"] * 8) / period_us
            implied_pct = (implied_bits_per_us / link_speed_bits_per_us) * 100
            print(f"Class: {traffic_class:<15} | Size: {config['size_bytes']:>4} Bytes | "
                  f"Fixed period_us: {period_us:>8.2f} µs (Load: {implied_pct:.4f}%)")
            computed_periods[traffic_class] = period_us

        # Option C: User specified link bandwidth budget allocation slice
        else:
            allocated_bits_per_us = link_speed_bits_per_us * config["pct"]
            packet_size_bits = config["size_bytes"] * 8
            period_us = packet_size_bits / allocated_bits_per_us
            computed_periods[traffic_class] = period_us

            print(f"Class: {traffic_class:<15} | Budget: {config['pct']*100:>3.0f}% | "
                  f"Size: {config['size_bytes']:>4} Bytes | Computed period_us: {period_us:>8.2f} µs")

    return computed_periods

def traffic_generator(env, switch, name, priority, period_us, pkt_size_bytes, is_periodic=True):
    pkt_id = 0
    while True:
        if is_periodic:
            yield env.timeout(period_us)
        else:
            yield env.timeout(np.random.exponential(scale=period_us))

        pkt_id += 1
        packet = {
            "ID": f"{name}_{pkt_id}",
            "Priority": priority,
            "Arrival": env.now,
            "Size_Bytes": pkt_size_bytes,
            "Class": name
        }
        switch.enqueue_packet(packet)

def visualize_results(df_metrics, sim_duration, cycle_time, test_name, traff_prof=None, gcl_sched=None):
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(12, 6.5))

    class_palette = {
        "Control_TT": "#10b981",
        "Mission_Crit": "#f59e0b",
        "Telemetry": "#3b82f6",
        "Best_Effort": "#ef4444",
    }

    if not df_metrics.empty:
        df_metrics["Class"] = df_metrics["Class"].str.strip()
    traffic_order = ["Control_TT", "Mission_Crit", "Telemetry", "Best_Effort"]

    sns.scatterplot(data=df_metrics,
                    x="Arrival", y="Latency",
                    hue="Class",
                    hue_order=traffic_order,
                    palette=class_palette,
                    s=50, alpha=0.8,
                    edgecolor="none",
                    linewidth=0)

    if gcl_sched:
        for cycle_base in np.arange(0, sim_duration, cycle_time):
            current_offset = 0.0
            for w_idx, w in enumerate(gcl_sched):
                w_dur = w["duration"]
                if w_idx == 0:
                    color, label_name = "#10b981", "TT Window"
                elif w_idx == 1:
                    color, label_name = "#f59e0b", "Crit Window"
                else:
                    color, label_name = "#64748b", "Shared Window"

                label = label_name if cycle_base == 0 else ""
                plt.axvspan(cycle_base + current_offset, cycle_base + current_offset + w_dur,
                            color=color, alpha=0.06, label=label)
                current_offset += w_dur

    plt.title(f"TSN Latency Profile: {test_name}", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Packet Arrival Time (µs)", fontsize=11)
    plt.ylabel("Queueing Latency (µs)", fontsize=11)
    plt.xlim(0, sim_duration)

    plt.legend(title="Traffic Classes / GCL Gates",
               bbox_to_anchor=(0.5, -0.15),
               loc="upper center",
               ncol=4,
               framealpha=0.95)

    if traff_prof and gcl_sched:
        info_text = "Traffic Profile:\n"
        for tc, cfg in traff_prof.items():
            if "rate_hz" in cfg:
                info_text += f"  {tc}: {cfg['rate_hz']} Hz\n"
            elif "pct" in cfg:
                info_text += f"  {tc}: {cfg.get('pct', 0)*100:.0f}%\n"
            else:
                info_text += f"  {tc}: {cfg.get('period_us', 0)}µs\n"

        info_text += "\nGCL Schedule:\n"
        for w in gcl_sched:
            info_text += f"  {w['duration']}µs -> {bin(w['gate_state'])}\n"

        plt.text(1.02, 0.98, info_text, transform=plt.gca().transAxes,
                 fontsize=9, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray'))

    plt.tight_layout()
    os.makedirs("plots", exist_ok=True)
    full_path = os.path.join("plots", f"{test_name}.png")
    plt.savefig(full_path, dpi=300, bbox_inches="tight")
    plt.close()

def run_tsn_simulation(test_case, gcl_sched, traff_prof, sim_duration=50000.0):
    traffic_periods = configure_tsn_traffic_periods(traff_prof, link_speed_gbps=1.0)
    cycle_time = sum(step["duration"] for step in gcl_sched)

    env = simpy.Environment()
    switch = TsnSwitch(env, link_speed_gbps=1.0, gcl_schedule=gcl_sched)

    for prof_name, val in traff_prof.items():
        if prof_name == "idle":
             continue
        is_periodic = val.get("cyclic", val.get("interval", True))
        prof_pktsz  = val.get("size_bytes", val.get("pkt_size", 200))
        prof_pri    = val.get("pri", val.get("priority", 0))
        prof_prd = traffic_periods[prof_name]

        env.process(
            traffic_generator(env, switch,
                    prof_name,
                    prof_pri,
                    prof_prd, prof_pktsz,
                    is_periodic)
        )

    env.run(until=sim_duration)
    results = switch.get_results()
    df_metrics = pd.DataFrame(results)

    if not df_metrics.empty:
        summary = df_metrics.groupby("Class")[["Latency"]].agg(["mean", "max", "count"])
        summary.columns = ["Mean Latency (µs)", "Max Latency (µs)", "Packet Count"]
        print(f"\n--- Summary for {test_case} ---")
        print(summary.round(2))
    else:
        print(f"\n--- Summary for {test_case} (No Packets Received) ---")

    visualize_results(df_metrics, sim_duration, cycle_time, test_case, traff_prof, gcl_sched)
