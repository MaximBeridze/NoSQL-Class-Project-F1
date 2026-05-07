from pydantic import BaseModel
from typing import Optional


class PointsUpdate(BaseModel):
    delta: float


class TrackScoreUpdate(BaseModel):
    score: float


class DriverStartPosition(BaseModel):
    driver_id: str
    start_position: int
    tyre: str = "Medium"


class InitRaceBody(BaseModel):
    race_name: str
    total_laps: int
    drivers: list[DriverStartPosition]


class LapUpdate(BaseModel):
    position: int
    lap: int
    gap_to_leader: str = "0.000"
    tyre: Optional[str] = None
    pit: bool = False
    status: str = "Racing"

