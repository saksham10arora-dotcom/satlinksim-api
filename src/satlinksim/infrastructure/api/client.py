import requests
from typing import List, Optional, Dict
from datetime import datetime
from satlinksim.infrastructure.api.schemas import SimulationRequest, SimulationResponse

class SatLinkSimClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        url = f"{self.base_url}/simulate"
        # Pydantic's model_dump_json() handles datetime serialization
        response = requests.post(url, data=request.model_dump_json(), headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return SimulationResponse.model_validate(response.json())

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
