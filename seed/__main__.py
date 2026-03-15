"""Idempotent seed script for ShipAPI database.

Creates demo data for showcasing the inventory management system:
- Demo admin user: demo@workermill.com / demo1234
- 20 categories (5 top-level + 15 subcategories)
- 50 products (45 active, 5 inactive)
- 3 warehouses (East Coast, West Coast, Central)
- 150 stock levels (~10 below threshold for alerts)
- 20 stock transfers with audit trail
- 50 audit log entries

This script is idempotent - safe to run multiple times.
"""

import random
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.auth import hash_password
from src.config import settings
from src.database import SessionLocal
from src.models import AuditLog, Category, Product, StockLevel, StockTransfer, User, Warehouse


def slugify(name: str) -> str:
    """Convert name to slug format."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def create_demo_user(db: Session) -> User:
    """Create or update the demo admin user."""
    # Check if demo user already exists
    result = db.execute(select(User).where(User.email == "demo@workermill.com"))
    demo_user = result.scalar_one_or_none()

    if demo_user:
        print("Demo user already exists, updating password...")
        demo_user.hashed_password = hash_password("demo1234")
        demo_user.is_admin = True
        demo_user.is_active = True
    else:
        print("Creating demo admin user...")
        demo_user = User(
            email="demo@workermill.com",
            username="demo_admin",
            hashed_password=hash_password("demo1234"),
            is_admin=True,
            is_active=True,
        )
        db.add(demo_user)

    db.flush()
    return demo_user


def create_categories(db: Session) -> list[Category]:
    """Create 20 categories (5 top-level + 15 subcategories)."""
    # Check if categories already exist
    result = db.execute(select(func.count(Category.id)))
    if result.scalar() >= 20:
        print("Categories already exist, skipping...")
        result = db.execute(select(Category))
        return list(result.scalars().all())

    print("Creating categories...")
    categories = []

    # Top-level categories
    top_level_data = [
        ("Electronics", "Electronic components and devices"),
        ("Industrial Tools", "Professional grade tools and equipment"),
        ("Safety Equipment", "Personal protective equipment and safety gear"),
        ("Office Supplies", "Business and office essentials"),
        ("Storage Solutions", "Containers and organization systems"),
    ]

    for name, description in top_level_data:
        category = Category(name=name, slug=slugify(name), description=description, parent_id=None)
        db.add(category)
        categories.append(category)

    db.flush()  # Get IDs for parent categories

    # Subcategories (3 per top-level category)
    subcategory_data = [
        # Electronics subcategories
        ("Sensors", "Various types of sensors and detection equipment", 0),
        ("Circuit Boards", "PCBs and electronic circuit components", 0),
        ("Cables & Connectors", "Wiring solutions and connection hardware", 0),
        # Industrial Tools subcategories
        ("Power Tools", "Electric and pneumatic power tools", 1),
        ("Hand Tools", "Manual tools and precision instruments", 1),
        ("Measuring Equipment", "Precision measurement and calibration tools", 1),
        # Safety Equipment subcategories
        ("Head Protection", "Helmets, hard hats, and protective headgear", 2),
        ("Eye & Face Protection", "Safety glasses, goggles, and face shields", 2),
        ("Respiratory Protection", "Masks, respirators, and breathing apparatus", 2),
        # Office Supplies subcategories
        ("Writing Materials", "Pens, pencils, and writing accessories", 3),
        ("Paper Products", "Various types of paper and forms", 3),
        ("Filing & Organization", "Folders, binders, and organizational tools", 3),
        # Storage Solutions subcategories
        ("Containers", "Bins, boxes, and storage containers", 4),
        ("Shelving Systems", "Racks, shelves, and storage structures", 4),
        ("Labels & Identification", "Tags, labels, and marking systems", 4),
    ]

    for name, description, parent_index in subcategory_data:
        subcategory = Category(
            name=name, slug=slugify(name), description=description, parent_id=categories[parent_index].id
        )
        db.add(subcategory)
        categories.append(subcategory)

    return categories


def create_products(db: Session, categories: list[Category]) -> list[Product]:
    """Create 50 products (45 active, 5 inactive)."""
    # Check if products already exist
    result = db.execute(select(func.count(Product.id)))
    if result.scalar() >= 50:
        print("Products already exist, skipping...")
        result = db.execute(select(Product))
        return list(result.scalars().all())

    print("Creating products...")
    products = []

    # Product data with realistic names and descriptions for good search testing
    product_data = [
        # Electronics - Sensors
        (
            "Digital Temperature Sensor",
            "DTS-001",
            "High-precision digital temperature sensor with I2C interface",
            Decimal("24.99"),
            True,
            "sensors",
        ),
        (
            "Motion Detection Sensor",
            "MDS-002",
            "PIR motion sensor for security and automation applications",
            Decimal("18.50"),
            True,
            "sensors",
        ),
        (
            "Pressure Sensor Module",
            "PSM-003",
            "Industrial pressure sensor with 4-20mA output",
            Decimal("89.99"),
            True,
            "sensors",
        ),
        # Electronics - Circuit Boards
        (
            "Arduino Compatible Board",
            "ACB-004",
            "Microcontroller development board compatible with Arduino IDE",
            Decimal("35.00"),
            True,
            "circuit-boards",
        ),
        (
            "Raspberry Pi Shield",
            "RPS-005",
            "GPIO expansion shield for Raspberry Pi projects",
            Decimal("28.75"),
            True,
            "circuit-boards",
        ),
        (
            "Motor Control PCB",
            "MCP-006",
            "H-bridge motor controller circuit board",
            Decimal("42.50"),
            True,
            "circuit-boards",
        ),
        # Electronics - Cables & Connectors
        (
            "USB-C Cable 2M",
            "UCC-007",
            "High-quality USB-C charging and data cable",
            Decimal("12.99"),
            True,
            "cables-connectors",
        ),
        (
            "Ethernet Connector Kit",
            "ECK-008",
            "RJ45 connectors with crimping tool",
            Decimal("29.99"),
            True,
            "cables-connectors",
        ),
        (
            "Power Cable Assembly",
            "PCA-009",
            "Industrial grade power cable with weatherproof connectors",
            Decimal("55.00"),
            True,
            "cables-connectors",
        ),
        # Industrial Tools - Power Tools
        (
            "Cordless Drill Set",
            "CDS-010",
            "18V cordless drill with battery and charger",
            Decimal("149.99"),
            True,
            "power-tools",
        ),
        (
            "Angle Grinder",
            "ANG-011",
            "Professional angle grinder with safety guard",
            Decimal("89.95"),
            True,
            "power-tools",
        ),
        (
            "Impact Driver",
            "IMP-012",
            "High-torque impact driver for heavy-duty applications",
            Decimal("125.00"),
            True,
            "power-tools",
        ),
        # Industrial Tools - Hand Tools
        (
            "Precision Screwdriver Set",
            "PSS-013",
            "15-piece precision screwdriver set with magnetic tips",
            Decimal("39.99"),
            True,
            "hand-tools",
        ),
        (
            "Digital Multimeter",
            "DMM-014",
            "Professional digital multimeter with auto-ranging",
            Decimal("79.99"),
            True,
            "hand-tools",
        ),
        (
            "Adjustable Wrench Set",
            "AWS-015",
            "Chrome vanadium steel adjustable wrench set",
            Decimal("45.50"),
            True,
            "hand-tools",
        ),
        # Industrial Tools - Measuring Equipment
        (
            "Digital Caliper",
            "DCA-016",
            "Stainless steel digital caliper with LCD display",
            Decimal("32.99"),
            True,
            "measuring-equipment",
        ),
        (
            "Laser Level",
            "LAS-017",
            "Self-leveling laser level with magnetic mount",
            Decimal("159.99"),
            True,
            "measuring-equipment",
        ),
        (
            "Torque Wrench",
            "TOR-018",
            "Click-type torque wrench with calibration certificate",
            Decimal("199.99"),
            True,
            "measuring-equipment",
        ),
        # Safety Equipment - Head Protection
        (
            "Hard Hat Type I",
            "HHT-019",
            "ANSI compliant hard hat with adjustable suspension",
            Decimal("24.99"),
            True,
            "head-protection",
        ),
        (
            "Climbing Helmet",
            "CLH-020",
            "Lightweight climbing helmet with ventilation",
            Decimal("89.99"),
            True,
            "head-protection",
        ),
        (
            "Welding Helmet",
            "WEL-021",
            "Auto-darkening welding helmet with grind mode",
            Decimal("179.99"),
            True,
            "head-protection",
        ),
        # Safety Equipment - Eye & Face Protection
        (
            "Safety Glasses Clear",
            "SGC-022",
            "Anti-fog safety glasses with UV protection",
            Decimal("15.99"),
            True,
            "eye-face-protection",
        ),
        (
            "Chemical Goggles",
            "CHG-023",
            "Chemical splash goggles with indirect ventilation",
            Decimal("28.50"),
            True,
            "eye-face-protection",
        ),
        (
            "Face Shield",
            "FAS-024",
            "Full face protection shield with anti-fog coating",
            Decimal("19.99"),
            True,
            "eye-face-protection",
        ),
        # Safety Equipment - Respiratory Protection
        (
            "N95 Respirator Box",
            "N95-025",
            "NIOSH approved N95 respirators, box of 20",
            Decimal("39.99"),
            True,
            "respiratory-protection",
        ),
        (
            "Half Face Respirator",
            "HFR-026",
            "Reusable half-face respirator with P100 filters",
            Decimal("89.99"),
            True,
            "respiratory-protection",
        ),
        (
            "Emergency Escape Mask",
            "EEM-027",
            "Self-rescue respirator for emergency evacuation",
            Decimal("299.99"),
            True,
            "respiratory-protection",
        ),
        # Office Supplies - Writing Materials
        (
            "Gel Pen Set",
            "GPS-028",
            "Smooth writing gel pens in assorted colors",
            Decimal("12.99"),
            True,
            "writing-materials",
        ),
        (
            "Mechanical Pencil",
            "MEC-029",
            "Professional mechanical pencil with lead refills",
            Decimal("8.99"),
            True,
            "writing-materials",
        ),
        (
            "Whiteboard Markers",
            "WBM-030",
            "Dry erase markers with fine tip",
            Decimal("15.99"),
            True,
            "writing-materials",
        ),
        # Office Supplies - Paper Products
        (
            "Copy Paper Ream",
            "CPR-031",
            "Premium copy paper, 500 sheets per ream",
            Decimal("9.99"),
            True,
            "paper-products",
        ),
        (
            "Sticky Notes Pack",
            "SNP-032",
            "Assorted sticky notes in multiple sizes",
            Decimal("7.99"),
            True,
            "paper-products",
        ),
        (
            "Legal Pads",
            "LEG-033",
            "Yellow legal pads, letter size, pack of 12",
            Decimal("19.99"),
            True,
            "paper-products",
        ),
        # Office Supplies - Filing & Organization
        (
            "File Folders",
            "FIF-034",
            "Manila file folders with tabs, box of 100",
            Decimal("24.99"),
            True,
            "filing-organization",
        ),
        ("Binder Set", "BIN-035", "3-ring binders in assorted colors", Decimal("29.99"), True, "filing-organization"),
        (
            "Document Organizer",
            "DOC-036",
            "Desktop document organizer with multiple slots",
            Decimal("34.99"),
            True,
            "filing-organization",
        ),
        # Storage Solutions - Containers
        (
            "Plastic Storage Bin",
            "PSB-037",
            "Clear plastic storage bin with secure lid",
            Decimal("18.99"),
            True,
            "containers",
        ),
        (
            "Metal Toolbox",
            "MET-038",
            "Heavy-duty metal toolbox with multiple compartments",
            Decimal("79.99"),
            True,
            "containers",
        ),
        (
            "Stackable Organizer",
            "STA-039",
            "Modular stackable organizer with dividers",
            Decimal("25.99"),
            True,
            "containers",
        ),
        # Storage Solutions - Shelving Systems
        (
            "Wire Shelf Unit",
            "WSU-040",
            "Adjustable wire shelf unit, 4 shelves",
            Decimal("119.99"),
            True,
            "shelving-systems",
        ),
        (
            "Heavy Duty Rack",
            "HDR-041",
            "Industrial heavy duty storage rack",
            Decimal("299.99"),
            True,
            "shelving-systems",
        ),
        (
            "Wall Mount Brackets",
            "WMB-042",
            "Heavy duty wall mount brackets for shelving",
            Decimal("39.99"),
            True,
            "shelving-systems",
        ),
        # Storage Solutions - Labels & Identification
        (
            "Label Maker",
            "LAB-043",
            "Portable label maker with LCD display",
            Decimal("49.99"),
            True,
            "labels-identification",
        ),
        (
            "Barcode Scanner",
            "BAR-044",
            "Handheld barcode scanner with USB cable",
            Decimal("89.99"),
            True,
            "labels-identification",
        ),
        (
            "Asset Tags",
            "ASS-045",
            "Durable asset identification tags, pack of 100",
            Decimal("29.99"),
            True,
            "labels-identification",
        ),
        # Inactive products (discontinued)
        ("Legacy Sensor Model", "LEG-046", "Discontinued temperature sensor model", Decimal("15.99"), False, "sensors"),
        ("Old Circuit Board", "OLD-047", "Obsolete microcontroller board", Decimal("25.00"), False, "circuit-boards"),
        ("Discontinued Cable", "DIS-048", "Legacy cable connector type", Decimal("8.99"), False, "cables-connectors"),
        ("Retired Tool", "RET-049", "Discontinued hand tool model", Decimal("19.99"), False, "hand-tools"),
        ("Obsolete Supplies", "OBS-050", "Legacy office supply item", Decimal("5.99"), False, "paper-products"),
    ]

    # Map category slugs to category objects
    category_map = {cat.slug: cat for cat in categories}

    for name, sku, description, price, is_active, category_slug in product_data:
        category = category_map.get(category_slug)
        if category is None:
            # Fallback to first category if slug not found
            category = categories[0]

        product = Product(
            name=name, sku=sku, description=description, price=price, is_active=is_active, category_id=category.id
        )
        db.add(product)
        products.append(product)

    db.flush()  # Get product IDs

    # Update search vectors for all products
    print("Updating search vectors...")
    for product in products:
        db.execute(
            text("UPDATE products SET search_vector = to_tsvector('english', name || ' ' || COALESCE(description, '')) WHERE id = :product_id"),
            {"product_id": str(product.id)},
        )

    return products


def create_warehouses(db: Session) -> list[Warehouse]:
    """Create 3 warehouses."""
    # Check if warehouses already exist
    result = db.execute(select(func.count(Warehouse.id)))
    if result.scalar() >= 3:
        print("Warehouses already exist, skipping...")
        result = db.execute(select(Warehouse))
        return list(result.scalars().all())

    print("Creating warehouses...")
    warehouse_data = [
        ("East Coast Distribution Center", "EAST", "1234 Industrial Blvd, Newark, NJ 07102"),
        ("West Coast Distribution Center", "WEST", "5678 Warehouse Way, Los Angeles, CA 90021"),
        ("Central Distribution Hub", "CENTRAL", "9012 Logistics Lane, Chicago, IL 60632"),
    ]

    warehouses = []
    for name, code, address in warehouse_data:
        warehouse = Warehouse(name=name, code=code, address=address, is_active=True)
        db.add(warehouse)
        warehouses.append(warehouse)

    return warehouses


def create_stock_levels(db: Session, products: list[Product], warehouses: list[Warehouse]) -> list[StockLevel]:
    """Create 150 stock level records (~10 below threshold for alerts)."""
    # Check if stock levels already exist
    result = db.execute(select(func.count(StockLevel.id)))
    if result.scalar() >= 150:
        print("Stock levels already exist, skipping...")
        result = db.execute(select(StockLevel))
        return list(result.scalars().all())

    print("Creating stock levels...")
    stock_levels = []

    # Create stock levels for active products across warehouses
    active_products = [p for p in products if p.is_active]

    random.seed(42)  # For consistent demo data

    low_stock_count = 0
    target_low_stock = 10

    for product in active_products:
        for warehouse in warehouses:
            # Generate realistic stock quantities
            if low_stock_count < target_low_stock and random.random() < 0.15:
                # Create low stock item (below threshold)
                quantity = random.randint(1, 8)
                threshold = 10
                low_stock_count += 1
            else:
                # Normal stock levels
                quantity = random.randint(15, 200)
                threshold = random.choice([10, 15, 20, 25])

            stock_level = StockLevel(
                product_id=product.id, warehouse_id=warehouse.id, quantity=quantity, low_stock_threshold=threshold
            )
            db.add(stock_level)
            stock_levels.append(stock_level)

            if len(stock_levels) >= 150:
                break

        if len(stock_levels) >= 150:
            break

    return stock_levels


def create_stock_transfers(
    db: Session, products: list[Product], warehouses: list[Warehouse], admin_user: User
) -> list[StockTransfer]:
    """Create 20 stock transfer records."""
    # Check if transfers already exist
    result = db.execute(select(func.count(StockTransfer.id)))
    if result.scalar() >= 20:
        print("Stock transfers already exist, skipping...")
        result = db.execute(select(StockTransfer))
        return list(result.scalars().all())

    print("Creating stock transfers...")
    transfers = []

    random.seed(42)  # For consistent demo data

    active_products = [p for p in products if p.is_active]

    for _i in range(20):
        # Select random product and warehouses
        product = random.choice(active_products)
        from_warehouse = random.choice(warehouses)

        # Ensure different source and destination warehouses
        to_warehouse = random.choice([w for w in warehouses if w.id != from_warehouse.id])

        # Random quantity and notes
        quantity = random.randint(5, 50)
        notes_options = [
            "Inventory rebalancing",
            "Emergency stock transfer",
            "Seasonal redistribution",
            "Customer demand adjustment",
            "Warehouse consolidation",
            None,  # Some transfers without notes
        ]
        notes = random.choice(notes_options)

        transfer = StockTransfer(
            product_id=product.id,
            from_warehouse_id=from_warehouse.id,
            to_warehouse_id=to_warehouse.id,
            quantity=quantity,
            notes=notes,
        )
        db.add(transfer)
        transfers.append(transfer)

    return transfers


def create_audit_logs(
    db: Session, admin_user: User, products: list[Product], categories: list[Category]
) -> list[AuditLog]:
    """Create 50 audit log entries."""
    # Check if audit logs already exist
    result = db.execute(select(func.count(AuditLog.id)))
    if result.scalar() >= 50:
        print("Audit logs already exist, skipping...")
        result = db.execute(select(AuditLog))
        return list(result.scalars().all())

    print("Creating audit log entries...")
    audit_logs = []

    random.seed(42)  # For consistent demo data

    actions = ["create", "update", "delete", "transfer"]
    resource_types = ["product", "category", "warehouse", "stock_level", "stock_transfer"]

    for _i in range(50):
        action = random.choice(actions)
        resource_type = random.choice(resource_types)

        # Select appropriate resource based on type
        if resource_type == "product":
            resource_id = random.choice(products).id
            details = {
                "action_type": action,
                "changes": {
                    "name": "Updated product name" if action == "update" else None,
                    "price": "Price changed to $99.99" if action == "update" else None,
                },
            }
        elif resource_type == "category":
            resource_id = random.choice(categories).id
            details = {
                "action_type": action,
                "changes": {
                    "name": "Updated category name" if action == "update" else None,
                    "description": "Updated description" if action == "update" else None,
                },
            }
        else:
            # Use a random UUID for other resource types
            resource_id = uuid.uuid4()
            details = {
                "action_type": action,
                "resource_type": resource_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        audit_log = AuditLog(
            user_id=admin_user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address="127.0.0.1",  # Demo IP address
        )
        db.add(audit_log)
        audit_logs.append(audit_log)

    return audit_logs


def main():
    """Main seed function."""
    print("Starting database seeding...")
    print(f"Database URL: {settings.DATABASE_URL}")

    # Create database session
    db = SessionLocal()

    try:
        # Create demo data in dependency order
        print("\n=== Creating Demo Data ===")

        # 1. Create demo user (admin)
        admin_user = create_demo_user(db)

        # 2. Create categories
        categories = create_categories(db)

        # 3. Create products
        products = create_products(db, categories)

        # 4. Create warehouses
        warehouses = create_warehouses(db)

        # 5. Create stock levels
        stock_levels = create_stock_levels(db, products, warehouses)

        # 6. Create stock transfers
        transfers = create_stock_transfers(db, products, warehouses, admin_user)

        # 7. Create audit logs
        audit_logs = create_audit_logs(db, admin_user, products, categories)

        # Commit all changes
        db.commit()

        print("\n=== Seed Summary ===")
        print(f"✓ Demo user: {admin_user.email}")
        print(f"✓ Categories: {len(categories)}")
        print(f"✓ Products: {len(products)} ({len([p for p in products if p.is_active])} active)")
        print(f"✓ Warehouses: {len(warehouses)}")
        print(f"✓ Stock levels: {len(stock_levels)}")
        print(f"✓ Stock transfers: {len(transfers)}")
        print(f"✓ Audit logs: {len(audit_logs)}")

        # Check low stock alerts
        low_stock_result = db.execute(
            select(func.count(StockLevel.id)).where(StockLevel.quantity < StockLevel.low_stock_threshold)
        )
        low_stock_count = low_stock_result.scalar()
        print(f"✓ Low stock alerts: {low_stock_count}")

        print("\n🎉 Database seeding completed successfully!")
        print("Demo credentials: demo@workermill.com / demo1234")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
