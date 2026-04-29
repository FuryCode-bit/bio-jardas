from collections.abc import AsyncGenerator
from typing import Any

import pytz
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.base import wrap_injection
from sqlalchemy.ext.asyncio import AsyncSession

from bio_jardas.bot import BioJardas
from bio_jardas.db.engine import transaction
from bio_jardas.domains.config.repositories import IntensityRepository
from bio_jardas.domains.config.services import IntensityService
from bio_jardas.domains.game.repositories import ScoreRepository, TimeoutCountRepository
from bio_jardas.domains.game.services import GameService
from bio_jardas.domains.message.repositories import (
    ChannelEnabledRepository,
    MessageGroupChoiceRepository,
    MessageGroupRepository,
    MessageRepository,
)
from bio_jardas.domains.message.services import MessageService
from bio_jardas.domains.time_gate.repositories import TimeGateRepository
from bio_jardas.domains.time_gate.services import TimeGateService
from bio_jardas.settings import SETTINGS


class SchedulerProvider(Provider):
    @provide(scope=Scope.APP)
    async def scheduler(self) -> AsyncIOScheduler:
        # TODO: use the engine and metadata we already have
        #  requires APScheduler v4, which hasn't been released yet
        #  https://github.com/agronholm/apscheduler/issues/465
        job_stores = {"default": SQLAlchemyJobStore(url=SETTINGS.postgres.sync_url)}
        job_defaults = {"coalesce": True, "max_instances": 1}
        return AsyncIOScheduler(
            jobstores=job_stores,
            job_defaults=job_defaults,
            timezone=pytz.timezone(SETTINGS.timezone),
        )


class BotProvider(Provider):
    @provide(scope=Scope.APP)
    async def bot(self, scheduler: AsyncIOScheduler) -> BioJardas:
        from bio_jardas.domains.config.cogs import IntensityCog
        from bio_jardas.domains.game.cogs import GameCog
        from bio_jardas.domains.message.cogs.fortune_teller import FortuneTellerCog
        from bio_jardas.domains.message.cogs.hug import HugCog
        from bio_jardas.domains.message.cogs.reply import ReplyCog
        from bio_jardas.domains.message.cogs.roast import RoastCog
        from bio_jardas.domains.message.cogs.vocabulary import VocabularyCog
        from bio_jardas.domains.schedule.cogs import ScheduleCog

        all_cogs = [
            IntensityCog,
            FortuneTellerCog,
            GameCog,
            HugCog,
            ReplyCog,
            RoastCog,
            ScheduleCog,
            VocabularyCog,
        ]

        bot = BioJardas.build(scheduler)
        for cog in all_cogs:
            bot.add_cog(cog(bot))
        return bot


class AsyncSessionProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def transaction(self) -> AsyncGenerator[AsyncSession, Any]:
        async with transaction() as session:
            yield session


class RepositoryProvider(Provider):
    scope = Scope.REQUEST

    @provide()
    async def message_repository(self, session: AsyncSession) -> MessageRepository:
        return MessageRepository(session)

    @provide()
    async def message_group_repository(
        self, session: AsyncSession
    ) -> MessageGroupRepository:
        return MessageGroupRepository(session)

    @provide()
    async def message_group_choice_repository(
        self, session: AsyncSession
    ) -> MessageGroupChoiceRepository:
        return MessageGroupChoiceRepository(session)

    @provide()
    async def channel_enabled_repository(
        self, session: AsyncSession
    ) -> ChannelEnabledRepository:
        return ChannelEnabledRepository(session)

    @provide()
    async def score_repository(self, session: AsyncSession) -> ScoreRepository:
        return ScoreRepository(session)

    @provide()
    async def timeout_count_repository(
        self, session: AsyncSession
    ) -> TimeoutCountRepository:
        return TimeoutCountRepository(session)

    @provide()
    async def time_gate_repository(self, session: AsyncSession) -> TimeGateRepository:
        return TimeGateRepository(session)

    @provide()
    async def intensity_repository(self, session: AsyncSession) -> IntensityRepository:
        return IntensityRepository(session)


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide()
    async def message_service(
        self,
        message_repo: MessageRepository,
        group_repo: MessageGroupRepository,
        choice_repo: MessageGroupChoiceRepository,
        channel_enabled_repo: ChannelEnabledRepository,
    ) -> MessageService:
        return MessageService(
            message_repo, group_repo, choice_repo, channel_enabled_repo
        )

    @provide()
    async def intensity_service(self, repo: IntensityRepository) -> IntensityService:
        return IntensityService(repo)

    @provide()
    async def game_service(
        self,
        bot: BioJardas,
        score_repo: ScoreRepository,
        timeout_count_repo: TimeoutCountRepository,
    ) -> GameService:
        return GameService(bot, score_repo, timeout_count_repo)

    @provide()
    async def time_gate_service(
        self, bot: BioJardas, gate_repo: TimeGateRepository
    ) -> TimeGateService:
        return TimeGateService(bot, gate_repo)


def _get_di_cog_container(*args, **_kwargs) -> AsyncContainer:
    return args[0][0].container


def cog_inject(func):
    return wrap_injection(
        func=func,
        is_async=True,
        scope=Scope.REQUEST,
        container_getter=_get_di_cog_container,
    )


def _get_di_job_inject(*_args, **_kwargs) -> AsyncContainer:
    return di_container


def job_inject(func):
    return wrap_injection(
        func=func,
        is_async=True,
        scope=Scope.REQUEST,
        container_getter=_get_di_job_inject,
    )


def build_di_container() -> AsyncContainer:
    return make_async_container(
        AsyncSessionProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        BotProvider(),
        SchedulerProvider(),
    )


di_container = build_di_container()
