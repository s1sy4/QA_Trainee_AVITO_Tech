import uuid

import allure
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Items")
@allure.story("E2E")
def test_should_create_and_delete_item_when_user_is_authorized(api_client):
    """
    E2E-001: Полный цикл: регистрация, авторизация, создание, получение, удаление
    """
    item_name = f"item_{uuid.uuid4().hex[:8]}"

    payload = {
        "name": item_name,
        "description": "E2E test item",
        "price": 5000,
        "sellerId": int(api_client["user_id"]),
        "statistics": {"contacts": 43, "likes": 21, "viewCount": 11},
    }

    with allure.step("Создание item через POST /api/1/item"):
        create_resp = api_client["create_item"](payload)

    with allure.step("Подтверждаем создание и проверяем данные через GET"):
        assert create_resp.status_code in [200, 201], f"Ошибка создания: {create_resp.text}"

        item_data = create_resp.json()
        status_message = item_data["status"]
        item_id = status_message.split(" - ")[1]
        get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
        assert get_resp.status_code == 200, f"Не удалось получить объявление: {get_resp.text}"

        item_from_api = get_resp.json()
        assert (
            item_from_api[0]["sellerId"] == api_client["user_id"]
        ), "sellerId не совпадает с userId"
        assert get_resp.json()[0]["name"] == item_name
        assert get_resp.json()[0]["price"] == 5000

    with allure.step(f"Получение item через GET /api/1/item/{item_id}"):
        get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")

    with allure.step(f"Удаление item через DELETE /api/2/item/{item_id}"):
        delete_resp = api_client["session"].delete(f"{BASE_URL}/2/item/{item_id}")
        assert delete_resp.status_code in [200, 204], f"Ошибка удаления: {delete_resp.text}"

    with allure.step("Проверяем, что item действительно удалён (GET должен вернуть 404)"):
        verify_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
        assert verify_resp.status_code == 404, "Item не удалён, всё ещё доступен!"
