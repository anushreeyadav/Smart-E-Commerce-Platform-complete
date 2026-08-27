from tests.conftest import add_to_cart


def test_inactive_product_is_hidden_and_cannot_be_added_to_cart(
    client, customer_headers, product, db_session
):
    product.is_active = False
    db_session.commit()

    listing = client.get("/products")
    assert listing.status_code == 200
    assert product.id not in {item["id"] for item in listing.json()}

    detail = client.get(f"/products/{product.id}")
    assert detail.status_code == 404

    cart_response = add_to_cart(client, customer_headers, product.id)
    assert cart_response.status_code == 404


def test_product_delete_is_a_soft_deactivation(
    client, admin_headers, product, db_session
):
    response = client.delete(
        f"/products/{product.id}", headers=admin_headers
    )

    assert response.status_code == 204
    db_session.refresh(product)
    assert product.is_active is False
