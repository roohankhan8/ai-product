"""Create the local development admin user if it does not already exist."""

import asyncio
import os

from sqlalchemy import select

from core.auth import hash_password
from database import session_factory
from models import Tenant, User


async def seed_admin() -> None:
    email = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "admin-password-change-me")
    tenant_slug = os.getenv("ADMIN_TENANT_SLUG", "local-workspace").strip()

    async with session_factory() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
        if tenant is None:
            tenant = Tenant(name="Local Workspace", slug=tenant_slug)
            session.add(tenant)
            await session.flush()

        user = await session.scalar(
            select(User).where(User.tenant_id == tenant.id, User.email == email)
        )
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=hash_password(password),
                display_name="Local Admin",
                role="admin",
                is_active=True,
            )
            session.add(user)
        else:
            user.role = "admin"
            user.is_active = True
            if password != "admin-password-change-me":
                user.password_hash = hash_password(password)

        await session.commit()
        print(f"Seeded admin user {email} in tenant {tenant.slug} ({tenant.id}).")
        print("Set ADMIN_PASSWORD before seeding to use a non-default password.")


if __name__ == "__main__":
    asyncio.run(seed_admin())
