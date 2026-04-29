import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from whenever import Instant

from bio_jardas.domains.game.enums import GameName
from bio_jardas.domains.game.models import Score, TimeoutCount
from bio_jardas.domains.game.repositories import (
    ScoreRepository,
    TimeoutCountRepository,
)
from bio_jardas.domains.game.services import GameService


@pytest.fixture
async def score_repo(session: AsyncSession) -> ScoreRepository:
    return ScoreRepository(session)


@pytest.fixture
async def timeout_count_repo(session: AsyncSession) -> TimeoutCountRepository:
    return TimeoutCountRepository(session)


@pytest.fixture
async def game_service(
    score_repo: ScoreRepository,
    timeout_count_repo: TimeoutCountRepository,
) -> GameService:
    return GameService(None, score_repo, timeout_count_repo)


async def test_score_get_or_create_new(score_repo: ScoreRepository) -> None:
    user_id = 123456789
    score_name = "test_game"

    score = await score_repo.get_or_create(user_id, score_name)

    assert score.user_snowflake_id == user_id
    assert score.name == score_name
    assert score.current == 0
    assert score.highest == 0
    assert score.id is not None

    # Verify whenever.Instant integration
    assert isinstance(score.created_at, Instant)
    assert isinstance(score.updated_at, Instant)


async def test_score_get_or_create_existing(score_repo: ScoreRepository) -> None:
    user_id = 123456789
    score_name = "test_game"

    # Create first
    original = Score(user_snowflake_id=user_id, name=score_name, current=10, highest=10)
    await score_repo.add(original)

    # Get again
    fetched = await score_repo.get_or_create(user_id, score_name)

    assert fetched.id == original.id
    assert fetched.current == 10
    assert fetched.highest == 10


async def test_score_get_or_create_for_update(score_repo: ScoreRepository) -> None:
    user_id = 123456789
    score_name = "test_game"

    # Just ensure it doesn't crash, as actual locking is
    # hard to test in a single session
    score = await score_repo.get_or_create(user_id, score_name, for_update=True)
    assert score.user_snowflake_id == user_id


async def test_get_high_scores_multiple_games(score_repo: ScoreRepository) -> None:
    # 2 games, 2 places each
    game1, game2 = "game1", "game2"

    scores = [
        # Game 1
        Score(user_snowflake_id=1, name=game1, highest=100),
        Score(user_snowflake_id=2, name=game1, highest=200),
        Score(user_snowflake_id=3, name=game1, highest=50),
        # Game 2
        Score(user_snowflake_id=4, name=game2, highest=500),
        Score(user_snowflake_id=5, name=game2, highest=300),
        Score(user_snowflake_id=6, name=game2, highest=400),
    ]
    await score_repo.add_many(scores)

    high_scores = await score_repo.get_high_scores([game1, game2], places=2)

    assert len(high_scores) == 4

    g1_high = [s for s in high_scores if s.name == game1]
    g2_high = [s for s in high_scores if s.name == game2]

    assert len(g1_high) == 2
    assert {s.user_snowflake_id for s in g1_high} == {1, 2}

    assert len(g2_high) == 2
    assert {s.user_snowflake_id for s in g2_high} == {4, 6}


async def test_get_high_scores_with_ties(score_repo: ScoreRepository) -> None:
    game_name = "tie_game"

    scores = [
        Score(user_snowflake_id=1, name=game_name, highest=100),
        Score(user_snowflake_id=2, name=game_name, highest=100),
        Score(user_snowflake_id=3, name=game_name, highest=50),
    ]
    await score_repo.add_many(scores)

    # Places = 1, but there's a tie for 1st place.
    # func.rank() gives the same rank (1) to both 100s.
    high_scores = await score_repo.get_high_scores([game_name], places=1)

    assert len(high_scores) == 2
    assert {s.user_snowflake_id for s in high_scores} == {1, 2}


async def test_get_high_scores_sparse_data(score_repo: ScoreRepository) -> None:
    game_name = "sparse_game"

    score = Score(user_snowflake_id=1, name=game_name, highest=100)
    await score_repo.add(score)

    # Requesting 10 places, but only 1 exists
    high_scores = await score_repo.get_high_scores([game_name], places=10)

    assert len(high_scores) == 1
    assert high_scores[0].user_snowflake_id == 1


async def test_leaderboard_omits_empty_timeout_leaderboard(
    game_service: GameService,
) -> None:
    leaderboards = await game_service.leaderboard([GameName.TIMEOUT_COUNT], places=3)

    assert leaderboards == []


async def test_leaderboard_includes_timeout_counts(
    game_service: GameService,
    timeout_count_repo: TimeoutCountRepository,
) -> None:
    await timeout_count_repo.add(
        TimeoutCount(user_snowflake_id=1, total=5)
    )
    await timeout_count_repo.add(
        TimeoutCount(user_snowflake_id=2, total=2)
    )

    leaderboards = await game_service.leaderboard([GameName.TIMEOUT_COUNT], places=3)

    assert len(leaderboards) == 1
    assert leaderboards[0].name == GameName.TIMEOUT_COUNT
    assert [entry.value for entry in leaderboards[0].high_scores] == [5, 2]
