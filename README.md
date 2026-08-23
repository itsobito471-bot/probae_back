# probae — Backend

This directory will house the API server for the **probae** platform.

## Stack (Planned)

- Runtime: Node.js
- Framework: TBD (Express / Fastify / NestJS)
- Database: TBD
- Auth: TBD

## Getting Started

> API development will happen here. This directory is intentionally left empty for now.

```bash
# future setup instructions will go here
```

## Notes

- All environment variables will live in a `.env` file (see `.env.example` when added).
- The frontend at `../frontend` will consume this API.

for starting the app use 
uvicorn main:app --reload 
this command


for intializing alembic 
alembic init -t async alembic
use this command

for migrations use 
alembic revision --autogenerate -m "Initial schema setup"
for upgrade use 
alembic upgrade head

## Seeding the Database

To populate the database with initial master data (such as the default Admin user and the Meal Categories: Breakfast, Lunch, Dinner, Snack, Drinks), you can run the master seed script:

```bash
python seed.py
```

This script will safely insert the default records. If they already exist, it will skip them or update them with the default configuration without creating duplicates.