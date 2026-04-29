from collections import defaultdict

from disnake.ext.commands import Bot

from bio_jardas.domains.game.enums import GameName
from bio_jardas.domains.game.models import Score, TimeoutCount
from bio_jardas.domains.game.objects import HighScoreEntry, Leaderboard
from bio_jardas.domains.game.repositories import ScoreRepository, TimeoutCountRepository


class GameService:
    def __init__(
        self,
        bot: Bot | None,
        score_repo: ScoreRepository,
        timeout_count_repo: TimeoutCountRepository,
    ):
        self.bot = bot
        self.score_repo = score_repo
        self.timeout_count_repo = timeout_count_repo

    async def increase_score_by(
        self, user_snowflake_id: int, score_name: str, amount: int = 1
    ) -> Score:
        score = await self.score_repo.get_or_create(
            user_snowflake_id, score_name, for_update=True
        )
        score.increase_by(amount)
        return score

    async def reset_current_score(
        self, user_snowflake_id: int, score_name: str
    ) -> Score:
        score = await self.score_repo.get_or_create(
            user_snowflake_id, score_name, for_update=True
        )
        score.reset()
        return score

    async def increment_timeout_count(self, user_snowflake_id: int) -> TimeoutCount:
        timeout_count = await self.timeout_count_repo.get_or_create(
            user_snowflake_id, for_update=True
        )
        timeout_count.increment()
        return timeout_count

    async def leaderboard(self, score_names: list[GameName], places: int = 3):
        non_timeout_names = [n for n in score_names if n != GameName.TIMEOUT_COUNT]
        high_scores = await self.score_repo.get_high_scores(non_timeout_names, places)

        scores_by_name = defaultdict(list)
        for score in high_scores:
            scores_by_name[score.name].append(score)

        for name in scores_by_name:
            scores_by_name[name] = sorted(
                scores_by_name[name], key=lambda s: s.highest, reverse=True
            )

        leaderboards = []
        for name in score_names:
            if name == GameName.TIMEOUT_COUNT:
                top_counts = await self.timeout_count_repo.get_top_timeout_counts(
                    places
                )
                if top_counts:
                    entries = [
                        HighScoreEntry(c.user_snowflake_id, c.total)
                        for c in top_counts
                    ]
                    leaderboards.append(Leaderboard(name, entries))
            else:
                scores = scores_by_name.get(str(name), [])
                if scores:
                    entries = [
                        HighScoreEntry(s.user_snowflake_id, s.highest)
                        for s in scores
                    ]
                    leaderboards.append(Leaderboard(name, entries))

        return leaderboards
