import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import use

# wcrt = worst-case-responst-time

def calculate_pboo_wcrt(sigma, rho, path_nodes):
    """Calculates E2E WCRT using the Pay-Burst-Only-Once (PBOO) method."""
    min_R = min(node['R'] for node in path_nodes)
    if min_R < rho:
        return float('inf'), sum(node['T'] for node in path_nodes), min_R
    total_T = sum(node['T'] for node in path_nodes)
    e2e_wcrt = total_T + (sigma / min_R)
    return e2e_wcrt, total_T, min_R

# ==============================================================================
# 1. DEFINE HARDWARE & PATH CONSTANTS (3-Hop Network)
# ==============================================================================
LINK_SPEED = 1e9          # 1 Gbps physical links (bits/sec)
MAX_MTU_BITS = 1518 * 8   # 12,144 bits (used for low-pri blocking calculations)

def compute_wcrt_over_n_hops(hop_count, gcl_latencies, flows):
    # Construct a 3-hop path execution model for each independent flow
    flow_results = {}
    for name, spec in flows.items():
        sigma = spec["size_bytes"] * 8
        rho   = spec["rho"]

        # Simulate traversing 3 sequential nodes with this priority profiles
        node_profile = gcl_latencies[name]
        path_hops = []
        for _ in range(hop_count):
            path_hops.append(node_profile)

        wcrt, total_T, bottleneck_R = calculate_pboo_wcrt(sigma, rho, path_hops)
        flow_results[name] = {
            "wcrt": wcrt, "total_T": total_T, "bottleneck_R": bottleneck_R, "sigma": sigma, "rho": rho
        }

        print(f"Class: {name:<18} | Path Total T: {total_T*1e6:>8.2f} µs | E2E WCRT Bound: {wcrt*1e6:>8.2f} µs")
    return flow_results

# ==============================================================================
# 3. VISUALIZATION ENGINE (4-Flow Mathematical Envelopes)
# ==============================================================================
def format_input_legend(hop_count, traff_prof, gcl_sched):
    if traff_prof and gcl_sched:
        info_text = "Flow Profile:\n"
        for tc, cfg in traff_prof.items():
            s = f"  {tc}: "
            if "size_bytes" in cfg:
                s += f"{cfg['size_bytes']} Bytes, "
            if "rho" in cfg:
                s += f"{cfg['rho']/1e6:.1f} Mbps"
            info_text += s.strip(', ') + "\n"

        info_text += "\nPer-Hop Latency Bounds:\n"
        if isinstance(gcl_sched, dict):
            for tc, w in gcl_sched.items():
                info_text += f"  {tc}: R={w.get('R', 0)/1e6:.0f}Mbps, T={w.get('T', 0)*1e6:.1f}µs\n"
        return info_text
    return None

def visualize_results(test_name, flow_results, hop_count, flow_spec=None, gcl_sched=None):
    time_axis_us = np.linspace(0, 12000, 5000)
    time_axis_sec = time_axis_us * 1e-6

    # Plot configuration
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=False)
    axes = axes.flatten()

    colors = {
        "Control_TT": ("#10b981", "#059669"),   # Greens
        "Mission_Crit": ("#f59e0b", "#d97706"), # Ambers
        "Telemetry": ("#3b82f6", "#2563eb"),    # Blues
        "Best_Effort": ("#ef4444", "#dc2626")    # Reds
    }

    for idx, (name, res) in enumerate(flow_results.items()):
        ax = axes[idx]
        c_arr, c_srv = colors[name]

        # Calculate curves data arrays
        alpha = res["sigma"] + (res["rho"] * time_axis_sec)
        beta = res["bottleneck_R"] * (time_axis_sec - res["total_T"])
        beta = np.maximum(0, beta)

        # Draw Lines
        ax.plot(time_axis_us, alpha, label=r"Arrival $\alpha(t)$", color=c_arr, linewidth=2)
        ax.plot(time_axis_us, beta, label=r"Path Service $\beta(t)$", color=c_srv, linewidth=2)

        # Highlight the WCRT Horizontal Gap
        ax.hlines(y=res["sigma"], xmin=0, xmax=res["wcrt"]*1e6, colors="#475569", linestyles=":", linewidth=1.2)
        ax.scatter([res["wcrt"]*1e6], [res["sigma"]], color="#df2626", zorder=5, s=40)

        # Tailor X-limits dynamically so small values are readable alongside massive ones
        if idx == 0:
            ax.set_xlim(0, 150) # TT clears in microseconds
            ax.set_ylim(0, res["sigma"] * 3)
        else:
            ax.set_xlim(0, res["wcrt"] * 1e6 * 1.3) # Lower priorities scale to milliseconds
            ax.set_ylim(0, res["sigma"] * 2.5)

        ax.set_title(f"WCRT Envelope: {name}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Time Horizon (µs)", fontsize=9)
        ax.set_ylabel("Data Volume (Bits)", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper left", fontsize=9)

        # Overlay performance metrics text box
        ax.text(0.95, 0.15, f"Path Delay T: {res['total_T']*1e6:.1f} µs\nE2E WCRT: {res['wcrt']*1e6:.1f} µs",
                transform=ax.transAxes, fontsize=9, ha="right",
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='gray'))

    info_text = format_input_legend(hop_count, flow_spec, gcl_sched)
    if info_text:
        plt.text(1.02, 0.98, info_text, transform=plt.gca().transAxes,
                 fontsize=9, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray'))

    plt.suptitle("Multi-Hop TSN Network Calculus Bounds for 4 TAS Priorities", fontsize=14, fontweight="bold", y=0.98)

    plt.tight_layout()
    os.makedirs("plots", exist_ok=True)
    full_path = os.path.join("plots", f"{test_name}.png")
    plt.savefig(full_path, dpi=300, bbox_inches="tight")
    plt.show()

def wcrt_calculus_main():
    # 4 Traffic Profile Allocations (Matching our prior TAS configuration sizes)
    flowspec_1 = {
        "Control_TT":   {"size_bytes": 200,  "rho": 5e6},   # 5 Mbps
        "Mission_Crit": {"size_bytes": 400,  "rho": 10e6},  # 10 Mbps
        "Telemetry":    {"size_bytes": 600,  "rho": 15e6},  # 15 Mbps
        "Best_Effort":  {"size_bytes": 1200, "rho": 20e6}   # 20 Mbps
    }

    # ==============================================================================
    # 2. CALCULATE PER-HOP LATENCY LATENCIES (T) FOR EACH FLOW
    # ==============================================================================
    # Latency 'T' scales up significantly as priority drops due to closed GCL windows.
    # T = (Max time gate is closed within cycle) + (Non-preemption wire-blocking delay)
    gcl_latencies_1 = {
        "Control_TT":   {"R": 100e6, "T": 0.0 + (MAX_MTU_BITS / LINK_SPEED)},# No wait, blocked only by frame on wire
        "Mission_Crit": {"R": 100e6, "T": 1000e-6 + (MAX_MTU_BITS / LINK_SPEED)}, # Must wait through 1ms TT window
        "Telemetry":    {"R": 100e6, "T": 3000e-6 + (MAX_MTU_BITS / LINK_SPEED)}, # Must wait through TT + Crit windows
        "Best_Effort":  {"R": 50e6,  "T": 3000e-6 + (MAX_MTU_BITS / LINK_SPEED)}  # Shares bottleneck line rate (50Mbps)
    }

    hops = 3
    flow_results = compute_wcrt_over_n_hops(hops, gcl_latencies=gcl_latencies_1, flows=flowspec_1)
    visualize_results("wcrt_3_hop",
         flow_results, hops,
         flow_spec=flowspec_1,
         gcl_sched=gcl_latencies_1)

if __name__ == "__main__":
    use('Agg')
    wcrt_calculus_main()
