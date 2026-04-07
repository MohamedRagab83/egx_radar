"""Create SaaS tables and insert one simple test user."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from egx_radar.database.manager import DatabaseManager
from egx_radar.database.models import User, Plan, Subscription


def utc_now_naive() -> datetime:
    """Return naive UTC datetime for compatibility with existing DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def main() -> None:
    db = DatabaseManager()
    db.init_db()

    with db.get_session() as session:
        user = session.query(User).filter(User.email == "test@egxradar.com").first()
        if user is None:
            user = User(email="test@egxradar.com")
            user.set_password("ChangeMe123!")
            session.add(user)
            session.flush()

        plan = session.query(Plan).filter(Plan.name == "Starter").first()
        if plan is None:
            plan = Plan(name="Starter", price=19.99)
            session.add(plan)
            session.flush()

        subscription = session.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.plan_id == plan.id,
        ).first()
        if subscription is None:
            subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status="active",
                start_date=utc_now_naive(),
                end_date=utc_now_naive() + timedelta(days=30),
            )
            session.add(subscription)

    print("SaaS tables created.")
    print("Test user ready: test@egxradar.com")
    print("Test plan ready: Starter")


if __name__ == "__main__":
    main()
