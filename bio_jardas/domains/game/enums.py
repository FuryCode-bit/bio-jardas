from enum import StrEnum


class GameName(StrEnum):
    RUSSIAN_ROULETTE = "russian_roulette"
    HARDCORE_ROULETTE = "hardcore_roulette"
    GLOCK_ROULETTE = "glock_roulette"
    TIMEOUT_COUNT = "timeout_count"


class RouletteResult(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"
