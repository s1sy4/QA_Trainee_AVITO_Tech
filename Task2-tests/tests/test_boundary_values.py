import pytest
import uuid
import allure
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Boundary Values")
@allure.story("Price Validation")
class TestBoundaryValues:
    """Тесты граничных значений для поля price"""

    @pytest.mark.parametrize("price, expected_status, description", [
        (0, 400, "BV-001: Нулевая цена"),
        pytest.param(
            -1, 400, "BV-002: Отрицательная цена", 
            marks=pytest.mark.xfail(reason="BUG-API-01: Сервер не валидирует отрицательные цены и возвращает 200")
        ),
        (999999999, 200, "BV-003: Большое валидное значение"),
        pytest.param(
            999999999999999999, 400, "BV-004: Слишком большое значение", 
            marks=pytest.mark.xfail(reason="BUG-API-02: Сервер не ограничивает максимальное значение цены")
        ),
        ("abc", 400, "BV-005: Строка вместо числа"),
        (None, 400, "BV-006: Null значение"),
    ])
    @allure.title("BV: Проверка price={price} ({description}) | Ожидаемый статус: {expected_status}")
    def test_create_item_with_boundary_price(
        self, api_client, price, expected_status, description
    ):
        """
        Параметризованный тест для проверки граничных значений price.
        """
        item_name = f"item_{uuid.uuid4().hex[:8]}"

        payload = {
            "name": item_name,
            "description": f"Boundary value test: {description}",
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1}
        }

        if price is not None:
            payload["price"] = price

        with allure.step(f"Создаём объявление с price={price}"):
            create_resp = api_client["session"].post(
                f"{BASE_URL}/1/item",
                json=payload
            )

        with allure.step(f"Проверяем статус код: ожидаем {expected_status}"):
            assert create_resp.status_code == expected_status, \
                f"Ожидался статус {expected_status} для price={price}, но получен {create_resp.status_code}. Ответ: {create_resp.text}"

        if expected_status == 201:
            with allure.step("Проверяем, что объявление создано и доступно"):
                item_id = create_resp.json()["status"].split(" - ")[1]
                get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
                assert get_resp.status_code == 200, "Объявление не найдено после создания"
                item_data = get_resp.json()[0]
                assert item_data["price"] == price, f"Цена не совпадает: ожидалось {price}, получено {item_data['price']}"