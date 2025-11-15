import asyncio
import time
import json
from typing import List, Tuple, Dict, Set
import httpx
from faker import Faker
import uuid
import random
import statistics

fake = Faker()
BASE_URL = "http://localhost:8080"


def random_id(prefix: str) -> str:
    """Сгенерировать уникальный ID с префиксом."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def create_team(client: httpx.AsyncClient, num_users: int = 10) -> Tuple[str, List[str]]:
    """Создать команду с уникальными пользователями."""
    team_name = random_id("team")
    members = [
        {
            "user_id": random_id("u"),
            "username": fake.name(),
            "is_active": True,
        }
        for _ in range(num_users)
    ]
    response = await client.post(
        f"{BASE_URL}/team/add",
        json={"team_name": team_name, "members": members},
    )
    response.raise_for_status()
    return team_name, [m["user_id"] for m in members]


async def create_pr(client: httpx.AsyncClient, author_id: str) -> str:
    """Создать PR с уникальным ID."""
    pr_id = random_id("pr")
    response = await client.post(
        f"{BASE_URL}/pullRequest/create",
        json={
            "pull_request_id": pr_id,
            "pull_request_name": fake.sentence(),
            "author_id": author_id,
        },
    )
    response.raise_for_status()
    return pr_id


async def merge_pr_api(client: httpx.AsyncClient, pr_id: str):
    """Пометить PR как MERGED."""
    response = await client.post(f"{BASE_URL}/pullRequest/merge", json={"pull_request_id": pr_id})
    response.raise_for_status()


async def reassign_reviewer_api(
    client: httpx.AsyncClient, pr_id: str, old_user_id: str, new_user_id: str
):
    """Переназначить ревьювера."""
    response = await client.post(
        f"{BASE_URL}/pullRequest/reassign",
        json={
            "pull_request_id": pr_id,
            "old_user_id": old_user_id,
            "new_user_id": new_user_id,
        },
    )
    response.raise_for_status()


async def set_user_active_status_api(client: httpx.AsyncClient, user_id: str, status: bool):
    """Установить флаг активности пользователя."""
    response = await client.post(
        f"{BASE_URL}/users/setIsActive",
        json={"user_id": user_id, "is_active": status},
    )
    response.raise_for_status()


async def get_reviews_api(client: httpx.AsyncClient, user_id: str):
    """Получить PR'ы, где пользователь назначен ревьювером."""
    response = await client.get(f"{BASE_URL}/users/getReview", params={"user_id": user_id})
    response.raise_for_status()
    return response.json()


async def get_stats_api(client: httpx.AsyncClient):
    """Получить статистику по пользователям и PR."""
    response = await client.get(f"{BASE_URL}/stats")
    response.raise_for_status()
    return response.json()


async def get_team_api(client: httpx.AsyncClient, team_name: str):
    """Получить команду с участниками."""
    response = await client.get(f"{BASE_URL}/team/get", params={"team_name": team_name})
    response.raise_for_status()
    return response.json()


async def get_pr_details_api(client: httpx.AsyncClient, pr_id: str) -> Dict | None:
    """Получить детали PR, включая ревьюверов и статус.
    Предполагается эндпоинт GET /pullRequest?pr_id={pr_id}."""
    try:
        response = await client.get(f"{BASE_URL}/pullRequest?pr_id={pr_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


class RequestStats:
    def __init__(self, label: str):
        self.label = label
        self.count = 0
        self.server_errors = 0
        self.response_times: List[float] = []
        self.error_details: Dict[str, int] = {}

    def record_success(self, duration_ms: float):
        self.count += 1
        self.response_times.append(duration_ms)

    def record_error(self, error_type: str = "Unknown", http_status_code: int | None = None):
        self.count += 1
        self.error_details[error_type] = self.error_details.get(error_type, 0) + 1
        # Если это ошибка сервера (5xx), увеличиваем server_errors
        if http_status_code and 500 <= http_status_code < 600:
            self.server_errors += 1

    def print_results(self, test_duration: int):
        if not self.response_times and self.count == 0:
            print(f"\nРезультаты {self.label}: Нет данных.")
            return

        print(f"\nРезультаты {self.label}:")
        print(f"  Всего запросов: {self.count}")

        print(f"  Ошибок (5xx): {self.server_errors}")

        if self.count > 0:

            success_rate = (self.count - self.server_errors) / self.count * 100
            rps = self.count / test_duration
            print(f"  Успешность (без 5xx): {success_rate:.2f}%")
            print(f"  RPS: {rps:.2f}")
        else:
            print("  Успешность (без 5xx): 0.00%")
            print("  RPS: 0.00")

        if self.response_times:
            avg_time = statistics.mean(self.response_times)
            sorted_times = sorted(self.response_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            max_time = max(self.response_times)
            min_time = min(self.response_times)
            print(
                f"  Время ответа (мс): среднее={avg_time:.2f}, P50={p50:.2f}, P95={p95:.2f}, P99={p99:.2f}, макс={max_time:.2f}, мин={min_time:.2f}"
            )
        else:
            print("  Время ответа (мс): Нет данных")


class SharedData:
    """Класс для хранения общих изменяемых данных и их синхронизации."""

    def __init__(self):
        self.teams_data: Dict[str, List[str]] = {}
        self.user_to_team_map: Dict[str, str] = {}
        self.all_user_ids: List[str] = []

        self.all_pr_ids_open: Set[str] = set()
        self.all_pr_ids_merged: Set[str] = set()

        self._lock_open_prs = asyncio.Lock()
        self._lock_merged_prs = asyncio.Lock()
        self._lock_users = asyncio.Lock()
        self._lock_teams = asyncio.Lock()

    async def add_pr_open(self, pr_id: str):
        async with self._lock_open_prs:
            self.all_pr_ids_open.add(pr_id)

    async def merge_pr(self, pr_id: str):
        async with self._lock_open_prs:
            if pr_id in self.all_pr_ids_open:
                self.all_pr_ids_open.remove(pr_id)
        async with self._lock_merged_prs:
            self.all_pr_ids_merged.add(pr_id)

    async def get_random_open_pr(self) -> str | None:
        async with self._lock_open_prs:
            if not self.all_pr_ids_open:
                return None
            return random.choice(list(self.all_pr_ids_open))

    async def get_random_user(self) -> str | None:
        async with self._lock_users:
            if not self.all_user_ids:
                return None
            return random.choice(self.all_user_ids)

    async def get_all_user_ids_snapshot(self) -> List[str]:
        """Возвращает безопасную копию списка всех ID пользователей."""
        async with self._lock_users:
            return list(self.all_user_ids)

    async def get_users_in_team(self, team_name: str) -> List[str]:
        """Возвращает список user_ids для данной команды."""
        async with self._lock_teams:
            return list(self.teams_data.get(team_name, []))

    async def get_user_team(self, user_id: str) -> str | None:
        """Возвращает название команды пользователя."""
        async with self._lock_users:
            return self.user_to_team_map.get(user_id)

    async def get_random_team(self) -> Tuple[str | None, List[str] | None]:
        async with self._lock_teams:
            if not self.teams_data:
                return None, None
            team_name = random.choice(list(self.teams_data.keys()))
            return team_name, self.teams_data[team_name]

    async def add_team_data(self, team_name: str, user_ids: List[str]):
        async with self._lock_teams:
            self.teams_data[team_name] = user_ids
        async with self._lock_users:
            self.all_user_ids.extend(user_ids)
            for user_id in user_ids:
                self.user_to_team_map[user_id] = team_name


async def _setup_initial_data(
    client: httpx.AsyncClient,
    shared_data: SharedData,
    num_teams: int,
    users_per_team: int,
    prs_per_team: int,
):
    """Создание предварительных данных: команды, пользователи, PR."""
    print("Создание предварительных данных...")
    start = time.time()

    for _ in range(num_teams):
        team_name, user_ids = await create_team(client, users_per_team)
        await shared_data.add_team_data(team_name, user_ids)
        for pr_num in range(prs_per_team):
            author_id = random.choice(user_ids)
            pr_id = await create_pr(
                client,
                author_id,
            )
            if pr_num % 2 == 0:
                await merge_pr_api(client, pr_id)
                await shared_data.merge_pr(pr_id)
            else:
                await shared_data.add_pr_open(pr_id)

    print(f"  Предварительные данные созданы за {time.time() - start:.2f}с\n")


async def _execute_read_request(
    client: httpx.AsyncClient, shared_data: SharedData, stats: RequestStats
):
    """Выполнить один случайный запрос на чтение и записать статистику."""
    req_start = time.time()
    try:
        request_type = random.randint(0, 2)

        if request_type == 0:
            user_id = await shared_data.get_random_user()
            if user_id:
                await get_reviews_api(client, user_id)
            else:
                raise ValueError("No users available for get_reviews")
        elif request_type == 1:
            await get_stats_api(client)
        elif request_type == 2:
            team_name, _ = await shared_data.get_random_team()
            if team_name:
                await get_team_api(client, team_name)
            else:
                raise ValueError("No teams available for get_team")

        stats.record_success((time.time() - req_start) * 1000)
    except httpx.HTTPStatusError as e:
        error_code = f"HTTP_ERROR_{e.response.status_code}"
        # Регистрируем ошибку, передавая HTTP статус код
        stats.record_error(error_code, e.response.status_code)
    except Exception as e:
        stats.record_error(type(e).__name__)


async def _execute_write_request(
    client: httpx.AsyncClient,
    shared_data: SharedData,
    stats: RequestStats,
):
    """Выполнить один случайный запрос на запись и записать статистику."""
    req_start = time.time()
    try:
        write_operation = random.randint(0, 3)

        if write_operation == 0:  # Мердж PR
            pr_id = await shared_data.get_random_open_pr()
            if not pr_id:
                raise ValueError("No open PRs to merge")

            pr_details = await get_pr_details_api(client, pr_id)
            if not pr_details:
                raise ValueError(f"PR {pr_id} not found for merge")
            if pr_details.get("status") == "MERGED":
                await shared_data.merge_pr(pr_id)
                raise ValueError(
                    f"PR {pr_id} already merged for merge operation (PR_MERGED_CLIENT_SIDE)"
                )

            await merge_pr_api(client, pr_id)
            await shared_data.merge_pr(pr_id)

        elif write_operation == 1:  # Переназначение ревьювера
            pr_id = await shared_data.get_random_open_pr()
            if not pr_id:
                raise ValueError("No open PRs for reassign reviewer")

            pr_details = await get_pr_details_api(client, pr_id)
            if not pr_details:
                raise ValueError(f"PR {pr_id} not found or inaccessible for reassign")

            if pr_details.get("status") == "MERGED":
                await shared_data.merge_pr(pr_id)
                raise ValueError(f"PR {pr_id} already merged for reassign (PR_MERGED_CLIENT_SIDE)")

            current_reviewers = [r["user_id"] for r in pr_details.get("reviewers", [])]

            if not current_reviewers:
                raise ValueError(
                    f"PR {pr_id} has no reviewers to reassign (NOT_ASSIGNED_CLIENT_SIDE)"
                )

            old_user_id = random.choice(current_reviewers)

            team_name_of_old_reviewer = await shared_data.get_user_team(old_user_id)
            if not team_name_of_old_reviewer:
                raise ValueError(
                    f"Team not found for old reviewer {old_user_id} (NO_TEAM_FOR_REVIEWER_CLIENT_SIDE)"
                )

            users_in_old_reviewer_team = await shared_data.get_users_in_team(
                team_name_of_old_reviewer
            )

            available_users_for_new_reviewer = [
                uid
                for uid in users_in_old_reviewer_team
                if uid != old_user_id and uid not in current_reviewers
            ]
            if not available_users_for_new_reviewer:
                raise ValueError(
                    f"No suitable new reviewer candidates in team {team_name_of_old_reviewer} for PR {pr_id} (NO_CANDIDATE_CLIENT_SIDE)"
                )
            new_user_id = random.choice(available_users_for_new_reviewer)

            await reassign_reviewer_api(client, pr_id, old_user_id, new_user_id)

        elif write_operation == 2:
            user_id = await shared_data.get_random_user()
            if user_id:
                status = random.choice([True, False])
                await set_user_active_status_api(client, user_id, status)
            else:
                raise ValueError("No users available for setting active status")

        elif write_operation == 3:
            author_id = await shared_data.get_random_user()
            if author_id:
                reviewer_ids_for_pr = []
                team_name_of_author = await shared_data.get_user_team(author_id)
                if team_name_of_author:
                    users_in_author_team = await shared_data.get_users_in_team(team_name_of_author)
                    potential_reviewers = [uid for uid in users_in_author_team if uid != author_id]
                    if potential_reviewers:
                        num_reviewers_to_assign = random.randint(
                            1, min(2, len(potential_reviewers))
                        )
                        reviewer_ids_for_pr = random.sample(
                            potential_reviewers, num_reviewers_to_assign
                        )

                new_pr_id = await create_pr(client, author_id, reviewer_ids_for_pr)
                await shared_data.add_pr_open(new_pr_id)
            else:
                raise ValueError("No users available to create PR")

        stats.record_success((time.time() - req_start) * 1000)
    except httpx.HTTPStatusError as e:
        error_info = {}
        try:
            error_info = e.response.json().get("error", {})
        except json.JSONDecodeError:
            pass

        error_code = error_info.get("code", f"HTTP_ERROR_{e.response.status_code}")

        stats.record_error(error_code, e.response.status_code)
    except ValueError as e:
        stats.record_error(f"CLIENT_ERROR_{e}")
    except Exception as e:
        stats.record_error(type(e).__name__)


async def run_load_test(
    num_teams: int = 1,
    users_per_team: int = 5,
    prs_per_team: int = 5,
    concurrent_reads: int = 30,
    concurrent_writes: int = 30,
    test_duration: int = 60,  # seconds
):
    print("Нагрузочное тестирование:")
    print(f"  Команд: {num_teams}")
    print(f"  Пользователей на команду: {users_per_team}")
    print(f"  PR на команду: {prs_per_team}")
    print(f"  Параллельных запросов на чтение: {concurrent_reads}")
    print(f"  Параллельных запросов на запись: {concurrent_writes}")
    print(f"  Длительность теста: {test_duration}с\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        shared_data = SharedData()
        await _setup_initial_data(client, shared_data, num_teams, users_per_team, prs_per_team)

        read_stats = RequestStats("тестирования чтения")
        write_stats = RequestStats("тестирования записи")

        end_time = time.time() + test_duration

        async def read_worker():
            while time.time() < end_time:
                await _execute_read_request(client, shared_data, read_stats)
                await asyncio.sleep(0.01)

        async def write_worker():
            while time.time() < end_time:
                await _execute_write_request(client, shared_data, write_stats)
                await asyncio.sleep(0.01)

        print("Запуск нагрузочного тестирования...")
        await asyncio.gather(
            *[read_worker() for _ in range(concurrent_reads)],
            *[write_worker() for _ in range(concurrent_writes)],
        )

        read_stats.print_results(test_duration)
        write_stats.print_results(test_duration)


if __name__ == "__main__":
    asyncio.run(
        run_load_test(
            num_teams=20,
            users_per_team=200,
            prs_per_team=50,
            concurrent_reads=60,
            concurrent_writes=60,
            test_duration=120,
        )
    )
