import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import FromDishka
from disnake import AllowedMentions
from disnake.ext.commands import Context, command
from structlog.contextvars import bind_contextvars

from bio_jardas.cogs import BaseCog
from bio_jardas.dependency_injection import cog_inject
from bio_jardas.domains.game.enums import GameName
from bio_jardas.domains.game.games.base import Game
from bio_jardas.domains.game.games.roulette import (
    GlockRoulette,
    HardcoreRoulette,
    RussianRoulette,
)
from bio_jardas.domains.game.games.shadowban import ShadowBanGame
from bio_jardas.domains.game.services import GameService

logger = structlog.stdlib.get_logger()


class GameCog(BaseCog):
    @command(name=GameName.RUSSIAN_ROULETTE)
    @cog_inject
    async def russian_roulette(
        self, context: Context, *, game_service: FromDishka[GameService]
    ) -> None:
        game = RussianRoulette(game_service)
        await _play_game(game, context)

    @command(name=GameName.HARDCORE_ROULETTE)
    @cog_inject
    async def hardcore_roulette(
        self, context: Context, *, game_service: FromDishka[GameService]
    ) -> None:
        game = HardcoreRoulette(game_service)
        await _play_game(game, context)

    @command(name=GameName.GLOCK_ROULETTE)
    @cog_inject
    async def glock_roulette(
        self, context: Context, *, game_service: FromDishka[GameService]
    ) -> None:
        game = GlockRoulette(game_service)
        await _play_game(game, context)

    @command(name="shadow")
    @cog_inject
    async def shadowban(
        self,
        context: Context,
        *,
        hours: int,
        game_service: FromDishka[GameService],
        scheduler: FromDishka[AsyncIOScheduler],
    ) -> None:
        game = ShadowBanGame(hours, game_service, scheduler)
        bind_contextvars(game=game.name)
        await game.play(context)

    @command(name="highscores")
    @cog_inject
    async def highscores(
        self, context: Context, *, game_service: FromDishka[GameService]
    ) -> None:
        leaderboards = await game_service.leaderboard(
            [
                GameName.RUSSIAN_ROULETTE,
                GameName.HARDCORE_ROULETTE,
                GameName.GLOCK_ROULETTE,
                GameName.TIMEOUT_COUNT,
            ]
        )
        leaderboard_displays = [lb.build_display() for lb in leaderboards]
        message = "\n\n".join(leaderboard_displays)
        await logger.ainfo("Leaderboards displayed")
        await context.send(message, allowed_mentions=AllowedMentions.none())


async def _play_game(game: Game, context: Context) -> None:
    result = await game.play(context)
    await logger.ainfo(
        "Game played",
        result=result.description,
        current_score=result.score.current,
        high_score=result.score.highest,
        game=GameName.RUSSIAN_ROULETTE,
    )
