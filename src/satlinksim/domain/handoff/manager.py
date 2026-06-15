import numpy as np
from satlinksim.domain.models import HandoffEvent

class HandoffManager:
    """
    Manages satellite selection and switching logic (handoffs).
    Prevents 'ping-ponging' using hysteresis and minimum dwell time.
    """
    def __init__(self, policy, hysteresis, min_dwell_steps):
        self.policy = policy  # "highest_elevation" or "highest_snr"
        self.hysteresis = hysteresis  # degrees if elevation, dB if SNR
        self.min_dwell_steps = min_dwell_steps
        
        self.current_sat_idx = None
        self.dwell_timer = 0
        self.events = []

    def select(self, step_idx: int, candidates_names: list, candidates_metrics: np.ndarray) -> int:
        """
        Select the best satellite index based on policy and constraints.
        candidates_metrics: array of values (elevation or SNR) for each candidate.
        """
        if len(candidates_metrics) == 0:
            return None
        
        best_idx = np.argmax(candidates_metrics)
        best_metric = candidates_metrics[best_idx]

        # Initial selection
        if self.current_sat_idx is None:
            self.current_sat_idx = best_idx
            self.dwell_timer = 0
            return self.current_sat_idx

        curr_metric = candidates_metrics[self.current_sat_idx]
        
        # Check if we SHOULD switch
        # 1. Is there a candidate significantly better than the current one? (Hysteresis)
        # 2. Have we stayed on the current satellite long enough? (Dwell time)
        
        should_switch = False
        if best_metric > (curr_metric + self.hysteresis):
            if self.dwell_timer >= self.min_dwell_steps:
                should_switch = True
            elif curr_metric < 0: # Emergency switch if link is lost (e.g. elevation < 0)
                should_switch = True

        if should_switch:
            self.events.append(HandoffEvent(
                time_step=step_idx,
                old_sat=candidates_names[self.current_sat_idx],
                new_sat=candidates_names[best_idx],
                reason=self.policy,
                metric_delta=float(best_metric - curr_metric)
            ))
            self.current_sat_idx = best_idx
            self.dwell_timer = 0
        else:
            self.dwell_timer += 1

        return self.current_sat_idx
