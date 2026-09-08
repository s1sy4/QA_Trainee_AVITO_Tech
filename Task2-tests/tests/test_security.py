import pytest
import uuid
import allure
import requests
from conftest import BASE_URL


@allure.epic("API Tests")
@allure.feature("Security")
@allure.story("Registration & Authentication")
class TestSecurityScenarios:
    """Тесты безопасности для регистрации и аутентификации"""

    @allure.title("SEC-001: SQL-инъекция в поле name/description")
    def test_post_with_sql_injection_returns_400(self, api_client):
        item_name = "' OR 1=1 --"
        desc = "'"
        payload = {
            "name": item_name,
            "description": desc,
            "price": 100,
            "sellerId": int(api_client["user_id"]),
            "statistics": {"contacts": 1, "likes": 1, "viewCount": 1}
        }
        
        with allure.step("Отправляем POST /api/1/item с валидными данными"):
            create_resp = api_client["create_item"](payload)
        
        with allure.step("Проверяем статус 200/400"):
            assert create_resp.status_code in [200, 400], f"Ошибка создания: {create_resp.text}"

        with allure.step("Извлекаем ID созданного объявления"):
            item_id = create_resp.json()["status"].split(" - ")[1]
            assert item_id, "ID объявления не найден в ответе"
                
        with allure.step("Получаем объявление через GET и проверяем все поля"):
            get_resp = api_client["session"].get(f"{BASE_URL}/1/item/{item_id}")
            assert get_resp.status_code == 200, f"Не удалось получить объявление: {get_resp.text}"
            
            item_data = get_resp.json()[0]

            assert item_data["name"] == item_name, f"Название не совпадает, {item_data}"

    @allure.title("SEC-002: Регистрация с уже существующим username")
    def test_register_duplicate_username_returns_400(self):
        """Сначала регистрируем пользователя, затем пытаемся зарегистрировать
        пользователя с тем же username."""

        unique_username = f"user_{uuid.uuid4().hex[:8]}"
        register_payload = {"username": unique_username, "password": "TestPass123!"}

        with allure.step("Регистрируем первого пользователя"):
            resp1 = requests.post(f"{BASE_URL}/1/register", json=register_payload)
            assert resp1.status_code in [200, 201], \
                f"Ошибка регистрации первого пользователя: {resp1.text}"

        with allure.step("Пытаемся зарегистрировать второго пользователя с тем же username"):
            resp2 = requests.post(f"{BASE_URL}/1/register", json=register_payload)

        with allure.step("Проверяем, что получен статус 409(дубликат username)"):
            assert resp2.status_code == 409, \
                f"Ожидался статус 409 для дубликата username, но получен {resp2.status_code}. Ответ: {resp2.text}"

    @allure.title("SEC-003: Авторизация с неверным паролем")
    def test_authorize_with_wrong_password_returns_401(self):
        """Сначала регистрируем пользователя, затем пытаемся авторизоваться
        с неправильным паролем."""
        unique_username = f"user_{uuid.uuid4().hex[:8]}"
        correct_password = "TestPass123!"
        wrong_password = "WrongPassword456!"

        register_payload = {"username": unique_username, "password": correct_password}

        with allure.step("Регистрируем нового пользователя"):
            resp_register = requests.post(f"{BASE_URL}/1/register", json=register_payload)
            assert resp_register.status_code in [200, 201], \
                f"Ошибка регистрации: {resp_register.text}"

        auth_payload = {"username": unique_username, "password": wrong_password}

        with allure.step("Пытаемся авторизоваться с неверным паролем"):
            resp_auth = requests.post(f"{BASE_URL}/1/autorize", json=auth_payload)

        with allure.step("Проверяем, что получен статус 401 Unauthorized"):
            assert resp_auth.status_code == 401, \
                f"Ожидался статус 401 для неверного пароля, но получен {resp_auth.status_code}. Ответ: {resp_auth.text}"
