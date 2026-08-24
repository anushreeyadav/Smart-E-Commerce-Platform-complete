from app.models.notification import NotificationType
from app.services.notification_service import create_notification


def _seed_notifications(db_session, user_id, count=5):
    created = []
    for i in range(count):
        created.append(
            create_notification(
                db_session,
                user_id=user_id,
                notification_type=NotificationType.ORDER_CONFIRMED,
                message=f"Notification {i}",
            )
        )
    return created


def test_list_notifications_requires_auth(client):
    response = client.get("/notifications")
    assert response.status_code in (401, 403)


def test_list_notifications_returns_only_own(
    client, db_session, customer, other_customer, customer_headers
):
    _seed_notifications(db_session, customer.id, count=2)
    _seed_notifications(db_session, other_customer.id, count=3)

    response = client.get("/notifications", headers=customer_headers)
    body = response.json()

    assert body["total"] == 2
    assert all(True for _ in body["items"])


def test_pagination(client, db_session, customer, customer_headers):
    _seed_notifications(db_session, customer.id, count=5)

    page1 = client.get(
        "/notifications?page=1&page_size=2", headers=customer_headers
    ).json()
    assert len(page1["items"]) == 2
    assert page1["total"] == 5
    assert page1["total_pages"] == 3

    page3 = client.get(
        "/notifications?page=3&page_size=2", headers=customer_headers
    ).json()
    assert len(page3["items"]) == 1


def test_read_unread_filter(client, db_session, customer, customer_headers):
    notifications = _seed_notifications(db_session, customer.id, count=3)

    client.post(
        "/notifications/read",
        json={"notification_ids": [notifications[0].id], "mark_all": False},
        headers=customer_headers,
    )

    unread = client.get("/notifications?read=false", headers=customer_headers).json()
    read = client.get("/notifications?read=true", headers=customer_headers).json()

    assert unread["total"] == 2
    assert read["total"] == 1
    assert read["items"][0]["id"] == notifications[0].id


def test_mark_single_notification_as_read(client, db_session, customer, customer_headers):
    notifications = _seed_notifications(db_session, customer.id, count=2)

    response = client.post(
        "/notifications/read",
        json={"notification_ids": [notifications[0].id], "mark_all": False},
        headers=customer_headers,
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 1

    items = client.get("/notifications", headers=customer_headers).json()["items"]
    by_id = {item["id"]: item["read_status"] for item in items}
    assert by_id[notifications[0].id] is True
    assert by_id[notifications[1].id] is False


def test_mark_all_notifications_as_read(client, db_session, customer, customer_headers):
    _seed_notifications(db_session, customer.id, count=4)

    response = client.post(
        "/notifications/read",
        json={"notification_ids": [], "mark_all": True},
        headers=customer_headers,
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 4

    items = client.get("/notifications", headers=customer_headers).json()["items"]
    assert all(item["read_status"] for item in items)


def test_cannot_mark_another_users_notification_as_read(
    client, db_session, customer, other_customer, customer_headers
):
    other_notifications = _seed_notifications(db_session, other_customer.id, count=1)

    response = client.post(
        "/notifications/read",
        json={"notification_ids": [other_notifications[0].id], "mark_all": False},
        headers=customer_headers,
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 0

    db_session.refresh(other_notifications[0])
    assert other_notifications[0].read_status is False
