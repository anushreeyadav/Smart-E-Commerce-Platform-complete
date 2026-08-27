from app.core.security import create_refresh_token


def test_deactivated_user_cannot_use_existing_access_token(
    client, customer, customer_headers, db_session
):
    customer.is_active = False
    db_session.commit()

    response = client.get("/auth/me", headers=customer_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "This account has been deactivated"


def test_deactivated_user_cannot_refresh_token(client, customer, db_session):
    customer.is_active = False
    db_session.commit()
    refresh_token = create_refresh_token(
        data={"sub": customer.id, "role": customer.role.value}
    )

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 403
    assert response.json()["detail"] == "This account has been deactivated"
