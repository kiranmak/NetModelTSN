# ---  SWITCH ENGINE AND ARCHITECTURE ---
import simpy

class TsnSwitch:
    def __init__(self, env, link_speed_gbps=1.0, gcl_schedule=None):
        self.env = env
        self.queues = {3: [], 2: [], 1: [], 0: []}
        self.link_speed_bits_per_us = link_speed_gbps * 1000.0
        self.gcl_schedule = gcl_schedule
        self.cycle_time = sum(step["duration"] for step in gcl_schedule)
        self.env.process(self.egress_scheduler_loop())
        self.results = []

    def get_results(self):
        return self.results

    def get_active_gcl_mask(self):
        position = self.env.now % self.cycle_time
        elapsed = 0.0
        for step in self.gcl_schedule:
            elapsed += step["duration"]
            if position < elapsed:
                return step["gate_state"]
        return 0b0000

    def enqueue_packet(self, packet):
        self.queues[packet["Priority"]].append(packet)

    def egress_scheduler_loop(self):
        while True:
            gate_mask = self.get_active_gcl_mask()
            packet_transmitted = False

            # Strict priority scanning among open gates
            for q_idx in sorted(self.queues.keys(), reverse=True):
                gate_is_open = (gate_mask & (1 << q_idx)) != 0

                if gate_is_open and len(self.queues[q_idx]) > 0:
                    pkt = self.queues[q_idx].pop(0)
                    packet_transmitted = True

                    tx_delay_us = (pkt["Size_Bytes"] * 8) / self.link_speed_bits_per_us
                    yield self.env.timeout(tx_delay_us)

                    pkt["Departure"] = self.env.now
                    pkt["Latency"] = pkt["Departure"] - pkt["Arrival"]
                    self.results.append(pkt)
                    break

            if not packet_transmitted:
                yield self.env.timeout(1.0)

