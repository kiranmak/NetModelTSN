# Time Aware Shaper - Normal Operation

![Plots of 4 classes](1_TAS_10ms_cycle.png)

We are running a Gate Control List schedule of 10 ms cycle. Here, the split for High, Medium and Low priority is 20:30:50 ratio.
The gates open in the following manner - We say that During first part of the cycle only Q1 (High) is open. the second part of the cycle opens for Q1/Q2 and 
We are designing our switch with 4 proirity queues. They work as below scheduling for 4 types of traffic, Mission critical, Control traffic, telemtry and besteffort.

| Gate-cycle | bit-mask | Open-Cycle | Type of traffic |
| ------------| ----------| ------------| -----------------|
|   Q3      | 0b1000  |   | Control Traffic (periodic)|
|   Q3-Q2   | 0b1100  |   | Control + MissionCritical (periodic)|
|   Q2-Q1-Q0| 0b0111  |   | TT+BE+MC |


This plot represents a visual baseline of a Time-Sensitive Networking (TSN) Time-Aware Shaper
 (TAS - IEEE 802.1Qbv) in action. We have packet latency on the Y-axis against its exact arrival time on the
 X-axis over a span of 600,000 microseconds (600 ms).
Graph Analysis:
The graph breaks down exactly how the Gate Control List (GCL) is prioritizes
and isolates 4 traffic flows:
1. The Isolated Flow:
    - Control\_TT (Dark Blue Dots): A perfect flat line of dark blue dots locked at the
absolute floor of the graph (0 µs to ~10 µs latency).
    - This confirms absolute determinism. Every single time a high-priority Time-Triggered
(TT) control packet arrives, it encounters zero queuing delay. The gate is wide
open for it, and it immediately clears the wire with no jitter.

2. The Artificially Capped Flow:
    -  Mission\_Crit (Green Dots): A rigid, flat line of green dots locked precisely at the 3,000 µs latency line.
    - It confirms an an intentional scheduling structure. These packets are arriving
ahead of their allowed window (likely during the dedicated TT Window).
    - Because the gate for Queue 2 (Mission\_Crit) is closed during that period,
      these packets are forced to buffer and wait.
    - Because they arrive predictably and wait for the exact same amount of time until the Crit Window
      opens, their latency is uniform at 3,000 µs. They have zero jitter,
      but a fixed intentional delay.

3. The Shared, Bursty Flows:
   -  Telemetry & Best\_Effort (Light Blue & Orange Dots):
    -  Scattered dots spreading across the entire height of the graph, from 0 µs to up
        to the end at 5,000 µs
    - These represent asynchronous or traffic classes. These dot near 0 µs, were just lucky—it arrived
       exactly when the BE Window (Q2/Q1/Q0 Open) was active, and the queue was clear.
    - They climb up toward 4,000–5,000 µs, means that gates where closed when they arrived
      They had to sit in the switch's memory buffer, until the cycle came back around to open their
      gates.

Summary of Network Health:
The configuration and graph shows that algo is working.
    -  High-priority traffic (Control\_TT) is at zero delay.
    -  Lower-priority traffic (Best\_Effort) absorbs network congestion and latency spikes, and
       does not interfere with critical industrial or automotive control cycles.
