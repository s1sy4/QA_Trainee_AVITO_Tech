import uuid

import pytest
import requests

BASE_URL = "https://qa-internship.avito.com/api"


@pytest.fixture(scope="function")
def api_client():
    """Фикстура для работы с API: регистрация, авторизация и очистка."""
    session = requests.Session()

    unique_suffix = uuid.uuid4().hex[:8]
    username = f"test_user_{unique_suffix}"
    password = "StrongPassword123!"

    reg_response = session.post(
        f"{BASE_URL}/1/register", json={"username": username, "password": password}
    )
    assert reg_response.status_code == 200 or reg_response.status_code == 201, "Ошибка регистрации"
    user_data = reg_response.json()
    user_id = user_data.get("id")

    auth_response = session.post(
        f"{BASE_URL}/1/autorize", json={"username": username, "password": password}
    )
    assert auth_response.status_code == 200, "Ошибка авторизации"
    token = auth_response.json().get("accessToken")

    session.headers.update({"Authorization": f"Bearer {token}"})

    created_items = []

    def create_item(item_data: dict):
        item_data["sellerID"] = user_id
        response = session.post(f"{BASE_URL}/1/item", json=item_data)
        if response.status_code == 200 or response.status_code == 201:
            created_items.append(response.json().get("id"))
        return response

    yield {"session": session, "user_id": user_id, "token": token, "create_item": create_item}

    for item_id in created_items:
        try:
            session.delete(f"{BASE_URL}/2/item/{item_id}")
        except requests.exceptions.RequestException:
            pass


@pytest.fixture
def second_api_client():
    """Вторая независимая фикстура для тестов с двумя пользователями"""
    session = requests.Session()

    unique_username = f"user2_{uuid.uuid4().hex[:8]}"
    password = "TestPassword123!"

    # Регистрация второго пользователя
    reg_resp = session.post(
        f"{BASE_URL}/1/register", json={"username": unique_username, "password": password}
    )
    assert reg_resp.status_code in [200, 201]
    user_id = reg_resp.json()["id"]

    # Авторизация
    auth_resp = session.post(
        f"{BASE_URL}/1/autorize", json={"username": unique_username, "password": password}
    )
    assert auth_resp.status_code == 200
    token = auth_resp.json()["accessToken"]

    session.headers.update({"Authorization": f"Bearer {token}"})

    created_items = []

    def create_item(payload: dict):
        payload["sellerId"] = int(user_id)
        resp = session.post(f"{BASE_URL}/1/item", json=payload)
        if resp.status_code in [200, 201]:
            item_id = resp.json()["status"].split(" - ")[1]
            created_items.append(item_id)
        return resp

    yield {"session": session, "user_id": user_id, "token": token, "create_item": create_item}

    # Teardown для второго пользователя
    for item_id in created_items:
        try:
            session.delete(f"{BASE_URL}/2/item/{item_id}")
        except Exception:
            pass


@pytest.fixture(scope="function")
def fresh_session():
    """Фикстура для создания чистой сессии без токена"""
    return requests.Session()
