"""
File: tsnsim.py
    This file demonstrates the most basic form of Simulation of TSN TAS Switch behaviour.
    The simulation environment, simply creates 2 streams best_effort and time-tiggered.
    It simply computes if the gate is open fora traffic type, send traffic or wait.
"""

import simpy
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt


# --- Simulation Parameters ---
CYCLE_TIME = 100.0       # Total duration of the TSN cycle (ms)
TT_WINDOW_START = 0.0    # Time-Triggered gate opens
TT_WINDOW_END = 30.0     # Time-Triggered gate closes (duration: 30ms)
SIM_DURATION = 500.0     # Total simulation time (ms)

def get_current_gate(env_time):
    """Returns whether the high-priority Time-Triggered (TT) gate is OPEN or CLOSED."""
    position_in_cycle = env_time % CYCLE_TIME
    if TT_WINDOW_START <= position_in_cycle < TT_WINDOW_END:
        return "TT_OPEN"
    return "BE_OPEN"

def tt_traffic_generator(env, results, worker_id):
    """Generates scheduled, high-priority Time-Triggered (TT) packets."""
    packet_id = 0
    while True:
        # TT traffic is highly periodic, arriving precisely at the start of the cycle
        yield env.timeout(CYCLE_TIME)
        packet_id += 1
        arrival_time = env.now
        gate_status = get_current_gate(arrival_time)

        # In a well-scheduled TSN network, TT traffic arrives exactly when its gate is open
        transmission_delay = 2.0  # constant small delay
        departure_time = arrival_time + transmission_delay
        latency = departure_time - arrival_time

        results.append({
            "Packet_ID": f"TT_{packet_id}",
            "Type": "Time-Triggered (High-Pri)",
            "Arrival": arrival_time,
            "Departure": departure_time,
            "Latency": latency,
            "Gate_At_Arrival": gate_status
        })

def be_traffic_generator(env, results, worker_id):
    """Generates stochastic, un-scheduled Best-Effort (BE) traffic."""
    packet_id = 0
    while True:
        # Best-effort packets arrive randomly (Poisson process)
        yield env.timeout(np.random.exponential(scale=15.0))
        packet_id += 1
        arrival_time = env.now
        
        # Process transmission checking the TAS Gate
        current_time = arrival_time
        while True:
            gate_status = get_current_gate(current_time)
            if gate_status == "BE_OPEN":
                # BE gate is open, transmit packet
                transmission_delay = 5.0  # variable or fixed payload
                departure_time = current_time + transmission_delay
                break
            else:
                # TT gate is open; Best Effort traffic must buffer and wait until the window closes
                position_in_cycle = current_time % CYCLE_TIME
                time_to_wait = TT_WINDOW_END - position_in_cycle
                current_time += time_to_wait
        
        results.append({
            "Packet_ID": f"BE_{packet_id}",
            "Type": "Best-Effort (Low-Pri)",
            "Arrival": arrival_time,
            "Departure": departure_time,
            "Latency": departure_time - arrival_time,
            "Gate_At_Arrival": gate_status
        })

# Assuming 'results' is the list populated by the SimPy simulation run:

def visualize_results(results):
    # Convert to DataFrame to evaluate network metrics
    df_metrics = pd.DataFrame(results)

    # Set plotting style
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(11, 6))

    # 1. Plot the Packet Latencies
    sns.scatterplot(
        data=df_metrics,
        x="Arrival",
        y="Latency",
        hue="Type",
        palette={"Time-Triggered (High-Pri)": "#10b981", "Best-Effort (Low-Pri)": "#ef4444"},
        s=80,
        alpha=0.85,
        edgecolor="black",
        linewidth=0.7
    )

    # 2. Highlight the Protected TSN Gating Windows (0-30ms, 100-130ms, etc.)
    # This visually demonstrates the Time-Aware Shaper behavior
    for cycle_start in range(0, 500, 100):
        plt.axvspan(
            cycle_start, 
            cycle_start + 30, 
            color="#3b82f6", 
            alpha=0.15, 
            label="TT Window (Gate Open)" if cycle_start == 0 else ""
        )

    # 3. Graph Styling & Annotations
    plt.title("TSN Time-Aware Shaper (TAS): Packet Latency Profile", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Packet Arrival Time (ms)", fontsize=12)
    plt.ylabel("Latency / Queueing Delay (ms)", fontsize=12)
    plt.xlim(0, 500)
    plt.ylim(0, 40)

    # Add custom descriptive notes directly onto the graph context
    plt.text(15, 36, "TT Gate Open:\nBE Packets Blocked", color="#1e40af", fontsize=9, fontweight="bold", ha="center")
    plt.text(65, 36, "BE Gate Open:\nPackets Transmit", color="#475569", fontsize=9, fontweight="bold", ha="center")

    # Clean up layout and display legend
    plt.legend(title="Traffic Class / Window Status", loc="upper right", framealpha=0.95)
    plt.tight_layout()
    plt.show()

def show_table_results(simulation_results):
    # Print the names of the columns.
    print("{:<5} {:<5} {:<10}{:<10} {:<10} {:<10}".format(
            'PktID', ' Type', 'Arrival',
             'Departure', 'Latency','Gate_At_Arrival'))

    # print each data item.
    for result in simulation_results:
        value = list(result.values())
        pkt, tt, arr, dep, lat, gate = value
        tt = "BE" if tt.startswith("Best") else "TT"
        arr = "{0:0.3f}".format(arr)
        dep = "{0:0.3f}".format(dep)
        lat = "{0:0.3f}".format(lat)
        print("{:<5} {:<5} {:<10} {:<10} {:<10} {:<10}".format(
                pkt, tt, arr, dep, lat, gate))

def tsnsim_main():
    env = simpy.Environment()
    simulation_results = []

    env.process(tt_traffic_generator(env, simulation_results, "TT-GEN"))
    env.process(be_traffic_generator(env, simulation_results, "BE-GEN"))
    env.run(until=SIM_DURATION)
    #show_table_results(simulation_results)
    # Convert to DataFrame to evaluate network metrics
    df_metrics = pd.DataFrame(simulation_results)
    print(df_metrics.head(15).to_string(index=False))    

    print("Headers:", df_metrics.columns)
    #visualize_results(simulation_results)

# --- Execution ---
if __name__ == "__main__":
    tsnsim_main()
