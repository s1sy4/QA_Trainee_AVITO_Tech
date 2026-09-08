import uuid

import allure
import pytest
import requests
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Negative Scenarios")
@allure.story("Authorization")
class TestNegativeAuthorization:
    """Негативные тесты для проверки авторизации и доступа"""

    @allure.title("NEG-001: Попытка доступа к API без токена авторизации")
    def test_access_without_token_returns_401(self):
        """Используем чистую сессию без установленного токена."""
        session = requests.Session()

        with allure.step("Отправляем GET /api/1/item/1 без токена"):
            resp = session.get(f"{BASE_URL}/1/item/1")

        with allure.step("Проверяем, что получен статус 401 Unauthorized"):
            assert resp.status_code == 401, f"Ожидался статус 401 для запроса без токена, \
                но получен {resp.status_code}. Ответ: {resp.text}"

    @allure.title("NEG-002: Попытка доступа с невалидным токеном")
    def test_access_with_invalid_token_returns_401(self):
        """Создаём сессию с заведомо невалидным токеном."""
        session = requests.Session()
        invalid_token = "Bearer invalid_token_12345_fake"
        session.headers.update({"Authorization": invalid_token})

        with allure.step("Отправляем POST /api/1/item/1 с невалидным токеном"):
            resp = session.post(f"{BASE_URL}/1/item/1")

        with allure.step("Проверяем, что получен статус 401 Unauthorized"):
            assert (
                resp.status_code == 401
            ), f"Ожидался статус 401 для запроса с невалидным токеном, \
                но получен {resp.status_code}. Ответ: {resp.text}"


@allure.epic("API Tests")
@allure.feature("Negative Scenarios")
@allure.story("Create Item Validation")
class TestNegativeCreateItem:
    """Негативные тесты для создания объявлений с некорректными данными"""

    @pytest.mark.parametrize(
        "seller_id, expected_status, description",
        [
            (999999999, 400, "NEG-003: Чужой sellerId (не принадлежит текущему пользователю)"),
            (None, 400, "NEG-004: Отсутствие поля sellerId"),
        ],
    )
    @allure.title("NEG: Создание объявления с {desc}")
    def test_create_item_with_invalid_seller_id(
        self, api_client, seller_id, expected_status, description
    ):
        """
        Параметризованный тест для проверки валидации sellerId.
        """
        item_name = f"item_{uuid.uuid4().hex[:8]}"

        payload = {
            "name": item_name,
            "description": f"Negative test: {description}",
            "price": 1000,
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }

        if seller_id is not None:
            payload["sellerId"] = seller_id

        with allure.step(f"Создаём объявление с sellerId={seller_id}"):
            create_resp = api_client["session"].post(f"{BASE_URL}/1/item", json=payload)

        with allure.step(f"Проверяем статус код: ожидаем {expected_status}"):
            assert (
                create_resp.status_code == expected_status
            ), f"Ожидался статус {expected_status} для sellerId={seller_id}, \
                но получен {create_resp.status_code}. Ответ: {create_resp.text}"


@allure.epic("API Tests")
@allure.feature("Negative Scenarios")
@allure.story("Get Item Validation")
class TestNegativeGetItem:
    @allure.title("NEG-005: Получение несуществующего объявления")
    def test_get_item_with_incorrect_id(self, api_client):
        with allure.step("Отправляем запрос к несуществующему id"):
            get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{uuid.uuid4()}")
            assert (
                get_resp.status_code == 404
            ), f"Удалось получить несуществующее объявление: {get_resp.text}"


@allure.epic("API Tests")
@allure.feature("Negative Scenarios")
@allure.story("Get Item Validation")
class TestNegativeDeleteItem:
    @pytest.mark.xfail(reason="BUG-API-04: Сервер не проверяет права при удалении (IDOR)")
    @allure.title("NEG-006: Попытка удаления чужого объявления")
    def test_delete_item_with_wrong_sellerId(self, api_client, second_api_client):
        """Пользователь A создаёт объявление, пользователь B пытается его удалить"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": item_name,
            "description": "Test item for NEG-006",
            "price": 1000,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }

        with allure.step("Пользователь A создаёт объявление"):
            create_resp = api_client["create_item"](payload)
            assert create_resp.status_code in [200, 201]
            item_id = create_resp.json()["status"].split(" - ")[1]

        with allure.step(
            f"Пользователь B пытается удалить объявление пользователя A (ID: {item_id})"
        ):
            delete_resp = second_api_client["session"].delete(f"{BASE_URL}/2/item/{item_id}")
        if delete_resp.status_code != 403:
            allure.attach(
                f"Ожидаемый статус: 403\n"
                f"Фактический статус: {delete_resp.status_code}\n"
                f"Тело ответа: {delete_resp.text}",
                name="Доказательство бага",
                attachment_type=allure.attachment_type.TEXT,
            )
        if delete_resp.status_code == 200:
            verify = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
            if verify.status_code == 404:
                allure.attach(
                    "Объявление реально удалено! Баг подтверждён.",
                    name="Подтверждение уязвимости",
                    attachment_type=allure.attachment_type.TEXT,
                )
        with allure.step("Проверяем статус 403 Forbidden"):
            assert (
                delete_resp.status_code == 403
            ), f"Ожидался 403, получен {delete_resp.status_code}"
