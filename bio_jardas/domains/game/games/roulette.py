import random
from abc import ABC, abstractmethod
from datetime import timedelta

from disnake import Forbidden
from disnake.ext.commands import Context

import bio_jardas.exceptions as exc
from bio_jardas.domains.game.enums import GameName, RouletteResult
from bio_jardas.domains.game.games.base import Game
from bio_jardas.domains.game.objects import ScoreResult


class RouletteGame(Game[ScoreResult], ABC):
    title: str

    async def play(self, context: Context) -> ScoreResult:
        player = context.author

        if self._is_safe():
            await context.channel.send(f"{player.mention} is safe!")
            score = await self.game_service.increase_score_by(player.id, self.name)
            return ScoreResult(RouletteResult.ALIVE, score)

        score = await self.game_service.reset_current_score(player.id, self.name)
        try:
            await player.timeout(
                duration=self._timeout_timedelta(),
                reason=f"You bit a bullet in {self.title}!",
            )
            await self.game_service.increment_timeout_count(player.id)
            await context.channel.send(f"{player.mention} has died")
        except Forbidden as e:
            match e.code:
                case exc.MISSING_PERMISSION_CODE:
                    await context.channel.send(
                        f"{player.mention} was shot, but is too strong to be killed!"
                    )
                case _:
                    await context.channel.send(
                        f"Error timing out {player.mention}: {e}"
                    )

        return ScoreResult(RouletteResult.DEAD, score)

    @abstractmethod
    async def _is_safe(self):
        raise NotImplementedError

    @abstractmethod
    def _timeout_timedelta(self) -> timedelta:
        raise NotImplementedError


class RussianRoulette(RouletteGame):
    name = GameName.RUSSIAN_ROULETTE
    title = "Russian Roulette"

    def _is_safe(self):
        bullet = random.random()
        return bullet > 1 / 6

    def _timeout_timedelta(self) -> timedelta:
        return timedelta(hours=1)


class HardcoreRoulette(RouletteGame):
    name = GameName.HARDCORE_ROULETTE
    title = "Hardcore Roulette"

    timeout_weights = [
        (1 / 100, timedelta(days=1)),
        (5 / 100, timedelta(hours=6)),
        (10 / 100, timedelta(hours=3)),
        (20 / 100, timedelta(hours=2)),
        (24 / 100, timedelta(hours=1)),
        (14 / 100, timedelta(minutes=45)),
        (20 / 100, timedelta(minutes=30)),
        (10 / 100, timedelta(minutes=10)),
        (5 / 100, timedelta(minutes=5)),
        (1 / 100, timedelta(minutes=1)),
    ]
    timeout_probabilities = [w for w, _ in timeout_weights]
    timeout_durations = [d for _, d in timeout_weights]

    def _is_safe(self):
        bullet = random.random()
        return bullet > 1 / 3

    def _timeout_timedelta(self) -> timedelta:
        return random.choices(self.timeout_durations, self.timeout_probabilities)[0]


class GlockRoulette(RouletteGame):
    name = GameName.GLOCK_ROULETTE
    title = "Glock Roulette"

    def _is_safe(self):
        bullet = random.random()
        return bullet <= 1 / 99

    def _timeout_timedelta(self) -> timedelta:
        return timedelta(minutes=10)
