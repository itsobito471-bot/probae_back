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
## Deployment Strategy (Linux VPS + aaPanel)

For production deployment, we recommend using a standard Linux VPS managed via **aaPanel**. This allows for simple process management and background task scheduling.

### 1. Web Services (Supervisor)
Use **Supervisor** (available as a plugin in aaPanel) to manage and keep the FastAPI application alive.
- **Run Dir**: `/www/wwwroot/probae/Backend`
- **Start Command**: `/www/wwwroot/probae/Backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000` (or using Gunicorn)

### 2. Automated Background Tasks (aaPanel Cron)
The Probae platform relies on scheduled background tasks (e.g., the Daily Order Generation script). We use **aaPanel's built-in Scheduled Tasks (Cron) Manager** to guarantee tasks run exactly once without multi-worker race conditions.

#### How to configure new Cron Jobs in aaPanel:
1. Navigate to the **Cron** tab in aaPanel.
2. Click **Add Scheduled Task**.
3. Set the schedule (e.g., execute at `00:00` daily for plan generation).
4. Enter the command to execute the Python script using your virtual environment:
```bash
# Navigate to the backend directory
cd /www/wwwroot/probae/Backend

# Execute the specific task using the project's virtual environment
/www/wwwroot/probae/Backend/venv/bin/python -m app.tasks.generate_plan_orders
```

### 3. Background Task Queue (Celery + Redis)
For event-driven asynchronous tasks (like logging calorie consumption when an order is dispatched), Probae utilizes **Celery** backed by **Redis**. This ensures the main FastAPI threads are never blocked by heavy operations.

#### How to setup Celery on aaPanel:
1. **Install Redis**: Go to the aaPanel **App Store** and do a 1-click install of **Redis**.
2. **Install Python Dependencies**: Ensure you are in your project's virtual environment and run:
   ```bash
   pip install celery redis
   ```
3. **Configure Supervisor for Celery**: Go to the Supervisor plugin in aaPanel, and add a new daemon:
   - **Name**: `probae_celery_worker`
   - **Run User**: `www` (or your preferred user)
   - **Run Dir**: `/www/wwwroot/probae/Backend`
   - **Start Command**: `/www/wwwroot/probae/Backend/venv/bin/celery -A app.core.celery_app worker --loglevel=info`

