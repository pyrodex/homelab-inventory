# Database Migrations

This application uses Flask-Migrate for database schema versioning.

## Initial Setup

To initialize migrations (first time only):

```bash
flask db init
```

## Creating Migrations

After making changes to models in `models.py`:

```bash
flask db migrate -m "Description of changes"
```

## Applying Migrations

To apply pending migrations:

```bash
flask db upgrade
```

## Rolling Back

To rollback the last migration:

```bash
flask db downgrade
```

## In Docker

Migrations are automatically handled on startup, but you can manually run:

```bash
docker exec homelab-inventory-backend flask db upgrade
```

