import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import allure
import pytest
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Race Conditions")
class TestRaceConditions:
    """Тесты на race conditions"""

    @allure.story("Concurrent Requests")
    @allure.title("ADV-001: Race condition — два параллельных POST с одинаковыми данными")
    def test_concurrent_create_item_with_same_data(self, api_client):
        """Отправляет два параллельных POST запроса с одинаковыми данными.
        Проверяет, что система корректно обрабатывает конкурентные запросы"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"

        payload = {
            "name": item_name,
            "description": "test item for race condition",
            "price": 1500,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }

        created_responses = []
        errors = []

        def create_item_thread():
            """Функция для создания объявления в отдельном потоке"""
            session = api_client["session"]
            try:
                resp = session.post(f"{BASE_URL}/1/item", json=payload)
                return resp
            except Exception as e:
                errors.append(str(e))
                return None

        with allure.step("Подготовка данных для теста на race condition"):
            allure.attach(str(payload), name="Payload", attachment_type=allure.attachment_type.JSON)

        with allure.step("Отправка двух параллельных POST запросов через ThreadPoolExecutor"):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(create_item_thread), executor.submit(create_item_thread)]

                for future in as_completed(futures):
                    response = future.result()
                    if response is not None:
                        created_responses.append(response)

        with allure.step("Анализ результатов параллельного выполнения"):
            assert (
                len(created_responses) == 2
            ), f"Ожидали 2 ответа, получили {len(created_responses)}"

            status_codes = [resp.status_code for resp in created_responses]
            allure.attach(
                str(status_codes), name="Status Codes", attachment_type=allure.attachment_type.TEXT
            )

            # Собираем ID созданных объявлений
            created_item_ids = []
            for resp in created_responses:
                if resp.status_code in [200, 201]:
                    try:
                        item_id = resp.json()["status"].split(" - ")[1]
                        created_item_ids.append(item_id)
                    except (KeyError, IndexError):
                        pass

            allure.attach(
                str(created_item_ids),
                name="Created Item IDs",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Проверка корректности обработки race condition"):
            # Вариант 1: Оба объявления созданы с разными ID
            if len(created_item_ids) == 2:
                assert (
                    created_item_ids[0] != created_item_ids[1]
                ), "Оба объявления имеют одинаковый ID — возможна проблема!"
                allure.attach(
                    "Оба объявления созданы с разными ID",
                    name="Result",
                    attachment_type=allure.attachment_type.TEXT,
                )

            # Вариант 2: Одно создано, второе отклонено (тоже допустимо)
            elif len(created_item_ids) == 1:
                success_count = sum(1 for code in status_codes if code in [200, 201])
                assert success_count == 1, "Ожидали ровно 1 успешный ответ"
                allure.attach(
                    "Одно объявление создано, второе отклонено",
                    name="Result",
                    attachment_type=allure.attachment_type.TEXT,
                )

            else:
                pytest.fail(
                    f"Неожиданный результат: {len(created_item_ids)} созданных объявлений. "
                    f"Статусы: {status_codes}"
                )

        with allure.step("Проверка отсутствия ошибок в потоках"):
            assert len(errors) == 0, f"Ошибки в потоках: {errors}"


@allure.epic("API Tests")
@allure.feature("Performance")
class TestPerformance:
    """Тесты производительности"""

    @allure.story("Load Testing")
    @allure.title(
        "PERF-001: Замер времени получения списка объявлений продавца после создания 15 объявлений"
    )
    def test_get_seller_items_performance_after_creating_multiple_items(self, api_client):
        """
        PERF-001: Производительность GET /api/1/{sellerID}/item

        Создаёт 15 объявлений и замеряет время получения списка всех объявлений продавца.
        Проверяет, что все объявления вернулись и время ответа в пределах нормы.
        """
        NUM_ITEMS = 15
        MAX_RESPONSE_TIME_MS = 5000  # Максимальное время ответа 5 секунд

        created_items = []

        with allure.step(f"Создание {NUM_ITEMS} объявлений"):
            for i in range(NUM_ITEMS):
                item_name = f"item_{uuid.uuid4().hex[:8]}_{i}"
                payload = {
                    "name": item_name,
                    "description": f"performance test item {i}",
                    "price": 1000 + i,
                    "sellerId": int(api_client["user_id"]),
                    "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
                }

                create_resp = api_client["create_item"](payload)
                assert create_resp.status_code in [
                    200,
                    201,
                ], f"Ошибка создания item {i}: {create_resp.text}"
                item_id = create_resp.json()["status"].split(" - ")[1]
                created_items.append({"id": item_id, "name": item_name})

            allure.attach(
                f"Создано {len(created_items)} объявлений",
                name="Created Items Count",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step(f"Замер времени GET /api/1/{api_client['user_id']}/item"):
            seller_id = api_client["user_id"]

            start_time = time.time()
            get_resp = api_client["session"].get(f"{BASE_URL}/1/{seller_id}/item")
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000

            allure.attach(
                f"{response_time_ms:.2f} ms",
                name="Response Time (ms)",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Проверка статуса ответа"):
            assert get_resp.status_code == 200, f"Ошибка получения списка: {get_resp.text}"

        with allure.step("Проверка, что вернулся массив"):
            items_list = get_resp.json()
            assert isinstance(items_list, list), "Ответ должен быть массивом"
            allure.attach(
                f"Получено {len(items_list)} объявлений",
                name="Returned Items Count",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step(f"Проверка, что все {NUM_ITEMS} созданных объявлений вернулись"):
            returned_names = [item["name"] for item in items_list if isinstance(item, dict)]

            for created in created_items:
                assert (
                    created["name"] in returned_names
                ), f"Объяление '{created['name']}' не найдено в списке продавца"

            # Проверяем, что количество возвращённых объявлений не меньше созданного
            assert (
                len(items_list) >= NUM_ITEMS
            ), f"Ожидали минимум {NUM_ITEMS} объявлений, получили {len(items_list)}"

        with allure.step(f"Проверка времени ответа (< {MAX_RESPONSE_TIME_MS}ms)"):
            assert (
                response_time_ms < MAX_RESPONSE_TIME_MS
            ), f"Время ответа {response_time_ms:.2f}ms превышает лимит {MAX_RESPONSE_TIME_MS}ms"
            allure.attach(
                f"Время ответа {response_time_ms:.2f}ms (лимит {MAX_RESPONSE_TIME_MS}ms)",
                name="Performance Result",
                attachment_type=allure.attachment_type.TEXT,
            )
