from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime
import numpy as np

from satlinksim.domain.models import SatelliteGeometry

class Propagator(ABC):
    @abstractmethod
    def get_geometry_batch(self, identifier, dts: List[datetime], gs_lat: float, gs_lon: float, gs_alt: float) -> Optional[SatelliteGeometry]:
        pass

    @abstractmethod
    async def get_geometry_batch_async(self, identifier, dts: List[datetime], gs_lat: float, gs_lon: float, gs_alt: float) -> Optional[SatelliteGeometry]:
        pass

    @abstractmethod
    def get_geometry(self, identifier, dt: datetime, gs_lat: float, gs_lon: float, gs_alt: float) -> Optional[SatelliteGeometry]:
        pass

class RainModel(ABC):
    @abstractmethod
    def generate_batch(self, n_steps: int) -> np.ndarray:
        pass

    @abstractmethod
    def step(self) -> float:
        pass
