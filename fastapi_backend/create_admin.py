from decimal import Decimal

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.product import Product
from app.models.user import User, UserRole


DEMO_USERS = [
    {
        "name": "System Administrator",
        "email": "admin@example.com",
        "password": "Admin@12345",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Store Staff",
        "email": "staff@example.com",
        "password": "Staff@12345",
        "role": UserRole.STAFF,
    },
    {
        "name": "Demo Customer",
        "email": "customer@example.com",
        "password": "Customer@12345",
        "role": UserRole.CUSTOMER,
    },
]


DEMO_PRODUCTS = [
    {
        "name": "Wireless Headphones",
        "description": "Noise-isolating headphones with long battery life.",
        "category": "electronics",
        "price": Decimal("2499.00"),
        "stock": 12,
        "images": ["https://images.unsplash.com/photo-1518441312322-14ed3f9f6f31"],
        "popularity": 95,
    },
    {
        "name": "Smart Watch",
        "description": "Fitness tracking smart watch with notifications.",
        "category": "electronics",
        "price": Decimal("3999.00"),
        "stock": 8,
        "images": ["https://images.unsplash.com/photo-1523275335684-37898b6baf30"],
        "popularity": 88,
    },
    {
        "name": "Running Shoes",
        "description": "Comfortable lightweight shoes for everyday use.",
        "category": "fashion",
        "price": Decimal("3199.00"),
        "stock": 18,
        "images": ["https://images.unsplash.com/photo-1542291026-7eec264c27ff"],
        "popularity": 76,
    },
]


def create_user_if_missing(
    db,
    *,
    name: str,
    email: str,
    password: str,
    role: UserRole,
):
    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        existing_user.name = name
        existing_user.role = role
        if password:
            existing_user.password = hash_password(password)

        db.commit()
        db.refresh(existing_user)

        print(f"Updated {role.value} user: {email}")
        return existing_user

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"Created {role.value} user: {email}")
    return user


def create_product_if_missing(
    db,
    *,
    name,
    description,
    category,
    price,
    stock,
    images,
    popularity,
):
    existing_product = (
        db.query(Product)
        .filter(Product.name == name)
        .first()
    )

    if existing_product:
        existing_product.description = description
        existing_product.category = category
        existing_product.price = price
        existing_product.stock = stock
        existing_product.images = images
        existing_product.popularity = popularity

        db.commit()
        db.refresh(existing_product)

        print(f"Updated product: {name}")
        return existing_product

    product = Product(
        name=name,
        description=description,
        category=category,
        price=price,
        stock=stock,
        images=images,
        popularity=popularity,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    print(f"Created product: {name}")
    return product


def seed_demo_data():
    db = SessionLocal()

    try:
        for user_data in DEMO_USERS:
            create_user_if_missing(db, **user_data)

        for product_data in DEMO_PRODUCTS:
            create_product_if_missing(db, **product_data)

        print("\nDemo data seeded successfully.")

    except Exception as error:
        db.rollback()
        print(f"Error seeding demo data: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
