import uuid

import allure
import pytest
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Advanced Validation")
class TestAdvancedValidation:
    """Расширенная валидация полей при создании объявления"""

    @pytest.mark.parametrize(
        "name_value, price_value, expected_status, test_id, description",
        [
            (None, 1000, 400, "ADV-002", "name=null"),
            ("item_", [1000], 400, "ADV-003", "price=массив"),
            ("", 1000, 400, "ADV-004", "name=пустая строка"),
        ],
        ids=["name_null", "price_array", "name_empty"],
    )
    @allure.story("Type Validation")
    @allure.title("{test_id}: Валидация типа поля ({description})")
    def test_create_item_with_invalid_field_types_returns_400(
        self, api_client, name_value, price_value, expected_status, test_id, description
    ):
        """Проверяет, что API возвращает 400 при некорректных типах данных:"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"

        payload = {
            "name": name_value if name_value is not None else None,
            "description": f"test item for {test_id}",
            "price": price_value,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }
        if name_value == "":
            payload["name"] = ""
        elif name_value is None:
            payload["name"] = None
        else:
            payload["name"] = item_name

        with allure.step(f"Подготовка payload с невалидным полем: {description}"):
            allure.attach(str(payload), name="Payload", attachment_type=allure.attachment_type.JSON)

        with allure.step(f"Отправляем POST /api/1/item с невалидными данными ({test_id})"):
            create_resp = api_client["create_item"](payload)

        with allure.step(f"Проверяем, что получен статус {expected_status}"):
            assert create_resp.status_code == expected_status, (
                f"Ожидали {expected_status}, получили {create_resp.status_code}. "
                f"Ответ: {create_resp.text}"
            )

        with allure.step("Проверяем, что объявление не было создано"):
            if create_resp.status_code != 201:
                try:
                    response_data = create_resp.json()
                    assert "status" not in response_data or "Created" not in response_data.get(
                        "status", ""
                    ), "Объявление было создано несмотря на невалидные данные"
                except Exception:
                    pass


@allure.epic("API Tests")
@allure.feature("Statistics Comparison")
class TestStatisticsComparison:
    """Сравнение версий статистики"""

    @allure.story("Statistics v1 vs v2")
    @allure.title("ADV-005: Сравнение statistic v1 и v2 для одного объявления")
    def test_compare_statistics_v1_and_v2_for_same_item(self, api_client):
        """
        Создаёт объявление и проверяет, что обе версии статистики (/api/1/statistic/{id}
        и /api/2/statistic/{id}) возвращают одинаковые данные.
        """
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        statistics = {"contacts": 5, "likes": 10, "viewCount": 25}

        payload = {
            "name": item_name,
            "description": "test item for ADV-005",
            "price": 2500,
            "sellerId": int(api_client["user_id"]),
            "statistics": statistics,
        }

        with allure.step("Создание объявления через POST /api/1/item"):
            create_resp = api_client["create_item"](payload)
            assert create_resp.status_code in [200, 201], f"Ошибка создания: {create_resp.text}"
            item_id = create_resp.json()["status"].split(" - ")[1]
            allure.attach(item_id, name="Item ID")

        with allure.step("Получение статистики через GET /api/1/statistic/{id} (v1)"):
            get_v1_resp = api_client["session"].get(f"{BASE_URL}/1/statistic/{item_id}")
            assert get_v1_resp.status_code == 200, f"Ошибка получения v1: {get_v1_resp.text}"
            stats_v1 = get_v1_resp.json()[0]
            allure.attach(
                str(stats_v1), name="Statistics v1", attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Получение статистики через GET /api/2/statistic/{id} (v2)"):
            get_v2_resp = api_client["session"].get(f"{BASE_URL}/2/statistic/{item_id}")
            assert get_v2_resp.status_code == 200, f"Ошибка получения v2: {get_v2_resp.text}"
            stats_v2 = get_v2_resp.json()[0]
            allure.attach(
                str(stats_v2), name="Statistics v2", attachment_type=allure.attachment_type.JSON
            )

        with allure.step("Сравнение данных из v1 и v2"):
            assert (
                stats_v1["contacts"] == stats_v2["contacts"]
            ), f"contacts не совпадают: v1={stats_v1['contacts']}, v2={stats_v2['contacts']}"
            assert (
                stats_v1["likes"] == stats_v2["likes"]
            ), f"likes не совпадают: v1={stats_v1['likes']}, v2={stats_v2['likes']}"
            assert (
                stats_v1["viewCount"] == stats_v2["viewCount"]
            ), f"viewCount не совпадают: v1={stats_v1['viewCount']}, v2={stats_v2['viewCount']}"


@allure.epic("API Tests")
@allure.feature("Security")
class TestIDORVulnerability:
    """Тесты на IDOR уязвимости"""

    @pytest.mark.xfail(reason="BUG-API-04: Сервер не проверяет права при удалении (IDOR)")
    @allure.story("IDOR")
    @allure.title(
        "ADV-006: IDOR на GET — пользователь B пытается получить объявление пользователя A"
    )
    def test_user_b_cannot_get_user_a_item_returns_403_or_404(self, api_client, second_api_client):
        """Пользователь B пытается получить объявление, созданное пользователем A."""
        item_name = f"item_{uuid.uuid4().hex[:8]}"

        payload = {
            "name": item_name,
            "description": "test item for IDOR test",
            "price": 3000,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }

        with allure.step("Пользователь A создаёт объявление"):
            create_resp = api_client["create_item"](payload)
            assert create_resp.status_code in [200, 201], f"Ошибка создания: {create_resp.text}"
            item_id = create_resp.json()["status"].split(" - ")[1]
            allure.attach(item_id, name="Item ID (создан пользователем A)")

        with allure.step(
            f"Пользователь B пытается получить объявление через GET /api/1/item/{item_id}"
        ):
            get_resp = second_api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
            allure.attach(str(get_resp.status_code), name="Response Status Code")

        with allure.step("Проверяем, что доступ запрещён (403 или 404)"):
            assert get_resp.status_code in [403, 404], (
                f"IDOR уязвимость! Пользователь B получил доступ к чужому объявлению. "
                f"Статус: {get_resp.status_code}, Ответ: {get_resp.text}"
            )

        with allure.step(
            "Дополнительно проверяем, что пользователь B не видит объявление в списке"
        ):
            seller_items_resp = second_api_client["session"].get(
                f"{BASE_URL}/1/{api_client['user_id']}/item"
            )
            if seller_items_resp.status_code == 200:
                items_list = seller_items_resp.json()
                assert isinstance(items_list, list)
                item_ids = [item.get("id") for item in items_list if isinstance(item, dict)]
                assert item_id not in item_ids, "Чужое объявление найдено в списке!"
