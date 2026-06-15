import numpy as np
from abc import ABC, abstractmethod
from typing import Optional
from satlinksim.domain.models import HandoffEvent

class HandoffPolicy(ABC):
    @abstractmethod
    def select_best(self, current_sat_idx: Optional[int], dwell_timer: int, min_dwell_steps: int, hysteresis: float, snr_metrics: np.ndarray, el_metrics: np.ndarray) -> tuple[Optional[int], bool, str, float]:
        """
        Evaluate candidates and return the selected satellite.
        Returns:
            new_sat_idx: int or None
            should_switch: bool
            reason: str
            metric_delta: float
        """
        pass

class HighestElevationPolicy(HandoffPolicy):
    def select_best(self, current_sat_idx, dwell_timer, min_dwell_steps, hysteresis, snr_metrics, el_metrics):
        if len(el_metrics) == 0:
            return None, False, "", 0.0
            
        best_idx = int(np.argmax(el_metrics))
        best_metric = el_metrics[best_idx]
        
        if current_sat_idx is None:
            return best_idx, True, "highest_elevation", 0.0
            
        curr_metric = el_metrics[current_sat_idx]
        should_switch = False
        
        if best_metric > (curr_metric + hysteresis):
            if dwell_timer >= min_dwell_steps:
                should_switch = True
            elif curr_metric < 0: # emergency switch
                should_switch = True
                
        return best_idx if should_switch else current_sat_idx, should_switch, "highest_elevation", float(best_metric - curr_metric)

class HighestSNRPolicy(HandoffPolicy):
    def select_best(self, current_sat_idx, dwell_timer, min_dwell_steps, hysteresis, snr_metrics, el_metrics):
        if len(snr_metrics) == 0:
            return None, False, "", 0.0
            
        best_idx = int(np.argmax(snr_metrics))
        best_metric = snr_metrics[best_idx]
        
        if current_sat_idx is None:
            return best_idx, True, "highest_snr", 0.0
            
        curr_metric = snr_metrics[current_sat_idx]
        should_switch = False
        
        if best_metric > (curr_metric + hysteresis):
            if dwell_timer >= min_dwell_steps:
                should_switch = True
            elif el_metrics[current_sat_idx] < 0: # emergency switch based on elevation
                should_switch = True
                
        return best_idx if should_switch else current_sat_idx, should_switch, "highest_snr", float(best_metric - curr_metric)

class HandoffManager:
    """
    Manages satellite selection and switching state using a provided HandoffPolicy.
    """
    def __init__(self, policy: HandoffPolicy, hysteresis: float, min_dwell_steps: int):
        self.policy = policy
        self.hysteresis = hysteresis
        self.min_dwell_steps = min_dwell_steps
        
        self.current_sat_idx = None
        self.dwell_timer = 0
        self.events = []

    def select(self, step_idx: int, candidates_names: list, snr_metrics: np.ndarray, el_metrics: np.ndarray) -> int:
        if len(snr_metrics) == 0:
            return None

        new_idx, should_switch, reason, delta = self.policy.select_best(
            self.current_sat_idx, self.dwell_timer, self.min_dwell_steps, self.hysteresis, snr_metrics, el_metrics
        )
        
        if self.current_sat_idx is None:
            self.current_sat_idx = new_idx
            self.dwell_timer = 0
            return self.current_sat_idx
            
        if should_switch:
            self.events.append(HandoffEvent(
                time_step=step_idx,
                old_sat=candidates_names[self.current_sat_idx],
                new_sat=candidates_names[new_idx],
                reason=reason,
                metric_delta=delta
            ))
            self.current_sat_idx = new_idx
            self.dwell_timer = 0
        else:
            self.dwell_timer += 1

        return self.current_sat_idx
