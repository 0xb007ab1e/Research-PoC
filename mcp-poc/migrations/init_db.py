"""
init_db.py

This script initializes a new tenant schema based on given tenant ID.
Using the provided tenant slug and configuration options, it will:
- Create the tenant entry in the main tenants table.
- Run any pending migrations for the tenant.

Usage:
  python init_db.py --tenant-slug=<tenant_slug>
"""

import os
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database_models import Tenant, get_all_metadata

# Set up argument parser for command line options
parser = argparse.ArgumentParser(description="Initialize new tenant database schema.")
parser.add_argument(
    "--tenant-slug", required=True, help="Slug of the tenant to initialize"
)
args = parser.parse_args()

# Setup database engine
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/mcp_db"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Create session
session = Session()

try:
    # Check if tenant already exists
    existing_tenant = session.query(Tenant).filter_by(slug=args.tenant_slug).first()
    if existing_tenant:
        print(f"Tenant with slug '{args.tenant_slug}' already exists.")
        exit(1)

    # Create new tenant entry
    new_tenant = Tenant(
        name=args.tenant_slug.title(), slug=args.tenant_slug.lower(), is_active=True
    )
    session.add(new_tenant)
    session.commit()

    # Run tenant-specific migrations
    tenant_id = new_tenant.id
    os.environ["TENANT_ID"] = str(tenant_id)
    os.system(f"alembic upgrade head")

    print(
        f"Tenant '{args.tenant_slug}' initialized with schema '{new_tenant.schema_name}'."
    )

finally:
    session.close()
