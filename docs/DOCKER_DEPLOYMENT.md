# Docker deployment

This Compose configuration starts PostgreSQL, FastAPI, Django, and the Next.js frontend on one local network.

## Start the stack

```powershell
cd smart
Copy-Item .env.docker.example .env
# Edit .env and replace the development secret values.
docker compose up --build -d
```

The first FastAPI startup creates the base application tables, applies the additive Alembic migrations, and seeds the demo users/products.

## URLs

- Storefront: `http://localhost:3000`
- FastAPI and Swagger: `http://localhost:8000/docs`
- Django admin: `http://localhost:8080/admin/`
- Django analytics: `http://localhost:8080/dashboard/`

## Create a Django administrator

The FastAPI demo administrator is separate from Django's built-in administrator account. Create a Django superuser once:

```powershell
docker compose exec django python manage.py createsuperuser
```

## Operations

```powershell
# Service logs
docker compose logs -f

# Stop services while keeping database data
docker compose down

# Stop services and remove the Docker database volume
docker compose down -v
```

`docker compose down -v` deletes the Docker-managed PostgreSQL data volume. It does not affect a locally installed PostgreSQL instance.
