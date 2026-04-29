from dataclasses import dataclass

from bio_jardas.domains.game.enums import GameName
from bio_jardas.domains.game.models import Score
from bio_jardas.utils import INFLECT, mention_by_snowflake_id, snake_case_to_title


@dataclass(frozen=True)
class HighScoreEntry:
    user_snowflake_id: int
    value: int


@dataclass(frozen=True)
class Leaderboard:
    name: GameName
    high_scores: list[HighScoreEntry]

    @property
    def title(self) -> str:
        return snake_case_to_title(self.name)

    def build_display(self) -> str:
        title = self.title
        lines = [f"**{title} Leaderboard**"]
        for index, entry in enumerate(self.high_scores, 1):
            place = f"{INFLECT.ordinal(index)} place"
            mention = mention_by_snowflake_id(entry.user_snowflake_id)
            score_line = f"{place}: {mention} - {entry.value}"
            lines.append(score_line)
        return "\n".join(lines)


@dataclass(frozen=True)
class ScoreResult:
    description: str
    score: Score
