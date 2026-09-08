import uuid

import allure
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Positive Scenarios")
class TestPositiveScenarios:
    """Позитивные тест-кейсы для API"""

    @allure.story("Registration")
    @allure.title("POS-001: Успешная регистрация нового пользователя")
    def test_register_new_user(self):
        """Регистрация с уникальным username"""
        import requests

        unique_username = f"user_{uuid.uuid4().hex[:8]}"
        payload = {"username": unique_username, "password": "TestPass123!"}

        with allure.step("Отправляем POST /api/1/register"):
            resp = requests.post(f"{BASE_URL}/1/register", json=payload)

        with allure.step("Проверяем статус 200/201 и наличие id"):
            assert resp.status_code in [200, 201], f"Ошибка регистрации: {resp.text}"
            data = resp.json()
            assert "id" in data, "Отсутствует поле id"
            assert data["username"] == unique_username, "Username не совпадает"

    @allure.story("Authorization")
    @allure.title("POS-002: Успешная авторизация существующего пользователя")
    def test_authorize_existing_user(self, api_client):
        """Авторизация с валидными credentials"""

        with allure.step("Проверяем, что токен получен"):
            assert api_client["token"], "Токен пустой"
            assert len(api_client["token"]) > 50, "Токен слишком короткий"

        with allure.step("Делаем запрос с токеном для проверки"):
            resp = api_client["session"].get(f"{BASE_URL}/1/item/999999")
            assert resp.status_code != 401, "Токен невалидный"

    @allure.story("Create Item")
    @allure.title("POS-003: Успешное создание объявления с корректным sellerId")
    def test_create_item_with_valid_seller_id_returns_201(self, api_client):
        """Создание объявления с валидными данными и корректным sellerId"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": item_name,
            "description": "test item for POS-003",
            "price": 1500,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }

        with allure.step("Отправляем POST /api/1/item с валидными данными"):
            create_resp = api_client["create_item"](payload)

        with allure.step("Проверяем статус 200/201"):
            assert create_resp.status_code in [200, 201], f"Ошибка создания: {create_resp.text}"

        with allure.step("Извлекаем ID созданного объявления"):
            item_id = create_resp.json()["status"].split(" - ")[1]
            assert item_id, "ID объявления не найден в ответе"

        with allure.step("Получаем объявление через GET и проверяем все поля"):
            get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
            assert get_resp.status_code == 200, f"Не удалось получить объявление: {get_resp.text}"

            item_data = get_resp.json()[0]

            assert item_data["name"] == item_name, "Название не совпадает"
            assert item_data["price"] == 1500, "Цена не совпадает"
            assert (
                item_data["sellerId"] == api_client["user_id"]
            ), "sellerId не совпадает с ID из токена"
            assert "createdAt" in item_data, "Отсутствует поле createdAt"

    @allure.story("Get Item")
    @allure.title("POS-004: Успешное получение объявления по ID")
    def test_get_item_by_id(self, api_client):
        """Получение существующего объявления"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": item_name,
            "description": "test item",
            "price": 1000,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1},
        }

        create_resp = api_client["create_item"](payload)
        assert create_resp.status_code in [200, 201]
        item_id = create_resp.json()["status"].split(" - ")[1]

        with allure.step(f"Отправляем GET /api/1/item/{item_id}"):
            get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")

        with allure.step("Проверяем статус 200 и данные"):
            assert get_resp.status_code == 200
            data = get_resp.json()[0]
            assert data["name"] == item_name
            assert data["price"] == 1000

    @allure.story("Get Seller's Items")
    @allure.title("POS-005: Успешное получение всех объявлений продавца")
    def test_get_all_items_by_seller_id_returns_200_with_array(self, api_client):
        """Получение списка всех объявлений конкретного продавца"""
        created_items = []
        for i in range(3):
            item_name = f"item_{uuid.uuid4().hex[:8]}_{i}"
            payload = {
                "name": item_name,
                "description": f"test item {i}",
                "price": 1000 + i,
                "sellerId": int(api_client["user_id"]),
                "statistics": {"contacts": 1, "likes": 2, "viewCount": 3},
            }
            create_resp = api_client["create_item"](payload)
            assert create_resp.status_code in [200, 201], f"Ошибка создания: {create_resp.text}"
            item_id = create_resp.json()["status"].split(" - ")[1]
            created_items.append({"id": item_id, "name": item_name})

        seller_id = int(api_client["user_id"])

        with allure.step(f"Отправляем GET /api/1/{seller_id}/item"):
            get_resp = api_client["session"].get(f"{BASE_URL}/1/{seller_id}/item")

        with allure.step("Проверяем статус 200 и что вернулся массив"):
            assert get_resp.status_code == 200, f"Ошибка получения списка: {get_resp.text}"
            items_list = get_resp.json()
            assert isinstance(items_list, list), "Ответ должен быть массивом"
            assert len(items_list) >= 3, f"Ожидали минимум 3 объявления, получили {len(items_list)}"

        with allure.step("Проверяем, что наши созданные объявления есть в списке"):
            returned_names = [item["name"] for item in items_list]
            for created in created_items:
                assert (
                    created["name"] in returned_names
                ), f"Объявление '{created['name']}' не найдено в списке продавца"

    @allure.story("Get Item Statictics v1")
    @allure.title("POS-006: Успешное получене статистики по объявлению v1")
    def test_get_statistic_v1_by_id(self, api_client):
        """Получение статистики по объявлению"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        statistics = {"contacts": 1, "likes": 2, "viewCount": 3}
        payload = {
            "name": item_name,
            "description": "test item",
            "price": 1000,
            "sellerId": int(api_client["user_id"]),
            "statistics": statistics,
        }
        create_resp = api_client["create_item"](payload)
        assert create_resp.status_code in [200, 201]
        item_id = create_resp.json()["status"].split(" - ")[1]

        with allure.step(f"Отправляем GET /api/1/statistic/{item_id}"):
            get_resp = api_client["session"].get(f"{BASE_URL}/1/statistic/{item_id}")

        with allure.step("Проверяем статус 200 и данные"):
            assert get_resp.status_code == 200
            data = get_resp.json()[0]
            assert data["contacts"] == statistics["contacts"]
            assert data["likes"] == statistics["likes"]
            assert data["viewCount"] == statistics["viewCount"]

    @allure.story("Get Item Statictics v2")
    @allure.title("POS-007: Успешное получене статистики по объявлению v2")
    def test_get_statistic_v2_by_id(self, api_client):
        """Получение статистики по объявлению"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        statistics = {"contacts": 1, "likes": 2, "viewCount": 1}
        payload = {
            "name": item_name,
            "description": "test item",
            "price": 1000,
            "sellerId": int(api_client["user_id"]),
            "statistics": statistics,
        }
        create_resp = api_client["create_item"](payload)
        assert create_resp.status_code in [200, 201]
        item_id = create_resp.json()["status"].split(" - ")[1]

        with allure.step(f"Отправляем GET /api/2/statistic/{item_id}"):
            get_resp = api_client["session"].get(f"{BASE_URL}/2/statistic/{item_id}")

        with allure.step("Проверяем статус 200 и данные"):
            assert get_resp.status_code == 200
            data = get_resp.json()[0]
            assert data["contacts"] == statistics["contacts"]
            assert data["likes"] == statistics["likes"]
            assert data["viewCount"] == statistics["viewCount"]

    @allure.story("Delete Item By Id")
    @allure.title("POS-008: Успешное удаление объявления")
    def test_delete_item_by_id(self, api_client):
        """Удаление объявления"""
        item_name = f"item_{uuid.uuid4().hex[:8]}"
        statistics = {"contacts": 1, "likes": 2, "viewCount": 1}
        payload = {
            "name": item_name,
            "description": "test item",
            "price": 400,
            "sellerId": int(api_client["user_id"]),
            "statistics": statistics,
        }
        create_resp = api_client["create_item"](payload)
        assert create_resp.status_code in [200, 201]
        item_id = create_resp.json()["status"].split(" - ")[1]

        with allure.step(f"Отправляем DELETE /api/2/item/{item_id}"):
            get_resp = api_client["session"].delete(f"{BASE_URL}/2/item/{item_id}")
        with allure.step("Проверяем статус 200 и повторно ищем объявление"):
            assert get_resp.status_code in [200, 204]
            get_resp2 = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
            assert get_resp2.status_code == 404
