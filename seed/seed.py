"""Seed script: populate the database with demo data.

Run as:
    python -m seed

Requires DATABASE_URL and JWT_SECRET_KEY environment variables (or a .env file).
"""

import asyncio
import datetime
import hashlib
import os
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import AuditLog, Category, Product, StockLevel, StockTransfer, User, Warehouse
from src.services.auth import get_api_key_prefix, hash_api_key, hash_password

# ---------------------------------------------------------------------------
# Admin user constants
# ---------------------------------------------------------------------------

ADMIN_EMAIL = "demo@workermill.com"
ADMIN_PASSWORD = "demo1234"
ADMIN_NAME = "Demo Admin"
ADMIN_ROLE = "admin"
ADMIN_API_KEY = "sk_demo_shipapi_2026_showcase_key"

# ---------------------------------------------------------------------------
# Category tree: 5 top-level with 3 subcategories each (15 subcategories total)
# ---------------------------------------------------------------------------

CATEGORY_TREE: list[dict] = [
    {
        "name": "Electronics",
        "description": "Electronic devices, computers, and accessories",
        "prefix": "ELEC",
        "children": [
            {
                "name": "Smartphones",
                "description": "Mobile phones and smartphones",
                "prefix": "SMT",
            },
            {"name": "Laptops", "description": "Portable computers and notebooks", "prefix": "LAP"},
            {
                "name": "Accessories",
                "description": "Electronic accessories and peripherals",
                "prefix": "ACC",
            },
        ],
    },
    {
        "name": "Clothing",
        "description": "Apparel, footwear, and fashion accessories",
        "prefix": "CLTH",
        "children": [
            {"name": "Men's", "description": "Men's clothing and apparel", "prefix": "MEN"},
            {"name": "Women's", "description": "Women's clothing and apparel", "prefix": "WMN"},
            {"name": "Kids'", "description": "Children's clothing and apparel", "prefix": "KDS"},
        ],
    },
    {
        "name": "Home & Garden",
        "description": "Home furnishings, kitchen equipment, and garden supplies",
        "prefix": "HOME",
        "children": [
            {"name": "Kitchen", "description": "Kitchen equipment and cookware", "prefix": "KIT"},
            {
                "name": "Outdoor",
                "description": "Outdoor furniture and garden tools",
                "prefix": "OUT",
            },
            {"name": "Decor", "description": "Home decorations and furnishings", "prefix": "DEC"},
        ],
    },
    {
        "name": "Sports",
        "description": "Sports equipment, activewear, and fitness accessories",
        "prefix": "SPRT",
        "children": [
            {"name": "Running", "description": "Running shoes and gear", "prefix": "RUN"},
            {"name": "Cycling", "description": "Bikes and cycling accessories", "prefix": "CYC"},
            {"name": "Swimming", "description": "Swimwear and pool equipment", "prefix": "SWM"},
        ],
    },
    {
        "name": "Books",
        "description": "Books, educational materials, and publications",
        "prefix": "BOOK",
        "children": [
            {"name": "Fiction", "description": "Novels and fiction literature", "prefix": "FCT"},
            {
                "name": "Technical",
                "description": "Technical and programming books",
                "prefix": "TCH",
            },
            {"name": "Business", "description": "Business and management books", "prefix": "BIZ"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Products: 50 products distributed across subcategories
# SKU format: {CATEGORY_PREFIX}-{SUBCATEGORY_PREFIX}-{3-digit number}
# 45 active + 5 inactive; rich descriptions for full-text search testing
# ---------------------------------------------------------------------------

PRODUCTS: list[dict] = [
    # ── Electronics > Smartphones (SMT) ── 3 products
    {
        "name": "NovaTech ProX 15 Smartphone",
        "sku": "ELEC-SMT-001",
        "description": (
            "The NovaTech ProX 15 features a 6.7-inch AMOLED display with 120 Hz refresh rate. "
            "Powered by the latest octa-core processor with 12 GB RAM for seamless multitasking. "
            "Its triple camera system delivers stunning 200 MP photos and 8K video recording."
        ),
        "price": Decimal("1199.99"),
        "weight_kg": Decimal("0.195"),
        "category_prefix": "SMT",
        "is_active": True,
    },
    {
        "name": "BrightStar Lite 8 Smartphone",
        "sku": "ELEC-SMT-002",
        "description": (
            "Budget-friendly BrightStar Lite 8 offers a 6.5-inch IPS display with vibrant colors. "
            "Dual SIM support with 5G connectivity makes it ideal for remote workers and travelers. "
            "Long-lasting 5000 mAh battery with 33 W fast charging included."
        ),
        "price": Decimal("299.99"),
        "weight_kg": Decimal("0.185"),
        "category_prefix": "SMT",
        "is_active": True,
    },
    {
        "name": "StellarPhone Ultra 5G",
        "sku": "ELEC-SMT-003",
        "description": (
            "Premium StellarPhone Ultra features a titanium frame and Gorilla Glass Victus protection. "
            "Satellite communication capability for emergency use in remote areas. "
            "Advanced AI photography with night mode and portrait enhancements for any lighting condition."
        ),
        "price": Decimal("1599.99"),
        "weight_kg": Decimal("0.220"),
        "category_prefix": "SMT",
        "is_active": True,
    },
    # ── Electronics > Laptops (LAP) ── 4 products
    {
        "name": "OmegaBook Pro 16",
        "sku": "ELEC-LAP-001",
        "description": (
            "OmegaBook Pro 16 delivers professional-grade performance with a 16-inch 4K OLED display. "
            "Equipped with Intel Core i9 and 32 GB DDR5 RAM for demanding creative workloads. "
            "Slim aluminum chassis weighs just 1.8 kg with all-day 18-hour battery life."
        ),
        "price": Decimal("2199.99"),
        "weight_kg": Decimal("1.800"),
        "category_prefix": "LAP",
        "is_active": True,
    },
    {
        "name": "CloudBook Air S",
        "sku": "ELEC-LAP-002",
        "description": (
            "Ultralight CloudBook Air S weighs just 1.2 kg and measures 13 mm thin. "
            "Perfect for students and commuters who need reliable productivity without the bulk. "
            "Fanless ARM-based processor ensures silent operation and 20-hour battery life."
        ),
        "price": Decimal("799.99"),
        "weight_kg": Decimal("1.200"),
        "category_prefix": "LAP",
        "is_active": True,
    },
    {
        "name": "GameForce RTX Gaming Laptop",
        "sku": "ELEC-LAP-003",
        "description": (
            "GameForce RTX dominates with RTX 5090 graphics and a 165 Hz QHD display for gaming. "
            "Liquid metal thermal compound keeps temperatures low during extended gaming sessions. "
            "Per-key RGB backlit keyboard with customizable macro profiles for esports competitors."
        ),
        "price": Decimal("2499.99"),
        "weight_kg": Decimal("2.400"),
        "category_prefix": "LAP",
        "is_active": True,
    },
    {
        "name": "WorkStation X1 Laptop",
        "sku": "ELEC-LAP-004",
        "description": (
            "Engineered for CAD, 3D rendering, and data science workloads in the field. "
            "Dual Thunderbolt 5 ports support external GPU and 8K display connections. "
            "MIL-SPEC durability tested for drops, spills, and extreme temperature ranges."
        ),
        "price": Decimal("1899.99"),
        "weight_kg": Decimal("2.100"),
        "category_prefix": "LAP",
        "is_active": True,
    },
    # ── Electronics > Accessories (ACC) ── 3 products
    {
        "name": "ProSound Wireless Earbuds",
        "sku": "ELEC-ACC-001",
        "description": (
            "ProSound wireless earbuds deliver audiophile-grade sound with active noise cancellation. "
            "30-hour total battery life with rapid charging case providing 5 hours in 10 minutes. "
            "IPX4 water resistance rating makes them suitable for workouts and rainy commutes."
        ),
        "price": Decimal("149.99"),
        "weight_kg": Decimal("0.060"),
        "category_prefix": "ACC",
        "is_active": True,
    },
    {
        "name": "UltraView 4K USB-C Monitor",
        "sku": "ELEC-ACC-002",
        "description": (
            "UltraView monitor features a 27-inch 4K IPS panel with 99% DCI-P3 color accuracy. "
            "Single USB-C cable provides power, video, and high-speed data transfer simultaneously. "
            "Built-in KVM switch lets one monitor serve two computers with a single keystroke."
        ),
        "price": Decimal("549.99"),
        "weight_kg": Decimal("4.200"),
        "category_prefix": "ACC",
        "is_active": True,
    },
    {
        "name": "QuickCharge 200W Desktop Hub",
        "sku": "ELEC-ACC-003",
        "description": (
            "Power up to 8 devices simultaneously with the QuickCharge 200 W desktop charging hub. "
            "Intelligent power distribution adjusts wattage automatically based on connected devices. "
            "USB-A, USB-C, and Qi wireless charging pads in a compact brushed aluminum design."
        ),
        "price": Decimal("89.99"),
        "weight_kg": Decimal("0.420"),
        "category_prefix": "ACC",
        "is_active": True,
    },
    # ── Clothing > Men's (MEN) ── 4 products
    {
        "name": "TrailBlaze Merino Wool Hoodie",
        "sku": "CLTH-MEN-001",
        "description": (
            "Crafted from 100% organic merino wool, this hoodie regulates temperature naturally. "
            "Anti-odor properties mean you can wear it multiple days without washing during travel. "
            "Machine washable and biodegradable with a relaxed fit for layering over base layers."
        ),
        "price": Decimal("129.99"),
        "weight_kg": Decimal("0.450"),
        "category_prefix": "MEN",
        "is_active": True,
    },
    {
        "name": "UrbanCore Slim Fit Chinos",
        "sku": "CLTH-MEN-002",
        "description": (
            "Premium stretch cotton blend chinos with four-way flex technology for unrestricted movement. "
            "Water-repellent DWR finish resists spills and light rain during everyday wear. "
            "Available in slim and straight cuts with an athletic fit through the thigh and knee."
        ),
        "price": Decimal("79.99"),
        "weight_kg": Decimal("0.380"),
        "category_prefix": "MEN",
        "is_active": True,
    },
    {
        "name": "VentMax Performance Polo",
        "sku": "CLTH-MEN-003",
        "description": (
            "Engineered with moisture-wicking UPF 50+ fabric to keep you cool during outdoor activities. "
            "Reinforced collar maintains its shape after 100+ wash cycles without ironing required. "
            "Available in 12 classic and seasonal colors for office-to-outdoors versatility."
        ),
        "price": Decimal("49.99"),
        "weight_kg": Decimal("0.200"),
        "category_prefix": "MEN",
        "is_active": True,
    },
    {
        "name": "Heritage Oxford Button-Down Shirt",
        "sku": "CLTH-MEN-004",
        "description": (
            "Classic Oxford weave shirt made from Egyptian cotton for superior softness and breathability. "
            "Mother-of-pearl buttons and reinforced stitching ensure long-lasting quality. "
            "Tailored fit with a slightly extended back yoke for comfortable desk-to-dinner wear."
        ),
        "price": Decimal("89.99"),
        "weight_kg": Decimal("0.280"),
        "category_prefix": "MEN",
        "is_active": False,  # inactive – 1 of 5
    },
    # ── Clothing > Women's (WMN) ── 3 products
    {
        "name": "FloWrap Bamboo Yoga Set",
        "sku": "CLTH-WMN-001",
        "description": (
            "Sustainable bamboo-modal blend yoga set featuring a strappy sports bra and high-waist leggings. "
            "Four-way stretch fabric moves with your body during hot yoga, Pilates, and barre classes. "
            "Side pockets deep enough for a full-sized phone without bounce during movement."
        ),
        "price": Decimal("95.99"),
        "weight_kg": Decimal("0.350"),
        "category_prefix": "WMN",
        "is_active": True,
    },
    {
        "name": "LuxeWool Cashmere Sweater",
        "sku": "CLTH-WMN-002",
        "description": (
            "Grade-A Mongolian cashmere sweater with a relaxed oversized silhouette perfect for layering. "
            "Hand-finished edges and reinforced elbows extend the lifespan of this wardrobe investment. "
            "Hypoallergenic and exceptionally soft against the skin, ideal for sensitive skin types."
        ),
        "price": Decimal("219.99"),
        "weight_kg": Decimal("0.400"),
        "category_prefix": "WMN",
        "is_active": True,
    },
    {
        "name": "AquaBreeze Linen Summer Dress",
        "sku": "CLTH-WMN-003",
        "description": (
            "European linen dress with a relaxed A-line cut ideal for beach vacations and summer dining. "
            "Natural breathability keeps you comfortable even in humid tropical conditions. "
            "Adjustable tie waist creates a flattering silhouette that transitions from day to evening."
        ),
        "price": Decimal("69.99"),
        "weight_kg": Decimal("0.250"),
        "category_prefix": "WMN",
        "is_active": True,
    },
    # ── Clothing > Kids' (KDS) ── 3 products
    {
        "name": "AdventureKid Waterproof Jacket",
        "sku": "CLTH-KDS-001",
        "description": (
            "Fully seam-sealed waterproof jacket rated 20,000 mm for rainy school days and outdoor play. "
            "Reflective strips on the arms and back provide visibility in low-light conditions. "
            "Packable into its own hood pocket for easy storage in any school backpack."
        ),
        "price": Decimal("59.99"),
        "weight_kg": Decimal("0.320"),
        "category_prefix": "KDS",
        "is_active": True,
    },
    {
        "name": "Dino Squad Organic Cotton Romper Set",
        "sku": "CLTH-KDS-002",
        "description": (
            "GOTS-certified organic cotton romper set with adorable dinosaur prints safe for sensitive skin. "
            "Snap buttons along the inseam make diaper changes quick and hassle-free for parents. "
            "Pre-shrunk fabric maintains true-to-size fit after repeated machine washing at 60°C."
        ),
        "price": Decimal("34.99"),
        "weight_kg": Decimal("0.180"),
        "category_prefix": "KDS",
        "is_active": True,
    },
    {
        "name": "GrowWith Me Adjustable School Backpack",
        "sku": "CLTH-KDS-003",
        "description": (
            "Ergonomic backpack with adjustable torso length that grows with children from ages 6-12. "
            "Padded laptop sleeve safely fits devices up to 13 inches for school and travel. "
            "Reflective safety strips and chest clip ensure secure wearing during bicycle rides."
        ),
        "price": Decimal("44.99"),
        "weight_kg": Decimal("0.520"),
        "category_prefix": "KDS",
        "is_active": False,  # inactive – 2 of 5
    },
    # ── Home & Garden > Kitchen (KIT) ── 3 products
    {
        "name": "ChefMaster Ceramic Knife Set",
        "sku": "HOME-KIT-001",
        "description": (
            "Professional-grade zirconia ceramic blades maintain razor sharpness 10x longer than steel. "
            "Set includes 8-inch chef, 6-inch utility, and 4-inch paring knife in an acacia wood block. "
            "Rustproof and non-reactive for acidic foods like tomatoes, citrus, and fermented vegetables."
        ),
        "price": Decimal("89.99"),
        "weight_kg": Decimal("0.650"),
        "category_prefix": "KIT",
        "is_active": True,
    },
    {
        "name": "VortexPro 1800W High-Speed Blender",
        "sku": "HOME-KIT-002",
        "description": (
            "Commercial-grade VortexPro blender pulverizes frozen fruit, nuts, and leafy greens smoothly. "
            "Self-cleaning program runs a 60-second automated wash cycle with warm water and soap. "
            "BPA-free 2 L container with vacuum lid eliminates oxidation for maximum nutrient retention."
        ),
        "price": Decimal("199.99"),
        "weight_kg": Decimal("3.200"),
        "category_prefix": "KIT",
        "is_active": True,
    },
    {
        "name": "Cast Iron Dutch Oven 5.5 Qt",
        "sku": "HOME-KIT-003",
        "description": (
            "Enameled cast iron retains heat evenly for slow-cooked soups, stews, and artisan bread. "
            "Organic enamel interior requires no seasoning and resists stains for easy cleaning. "
            "Compatible with all cooktops including induction, oven-safe to 500°F for braising."
        ),
        "price": Decimal("149.99"),
        "weight_kg": Decimal("5.800"),
        "category_prefix": "KIT",
        "is_active": True,
    },
    # ── Home & Garden > Outdoor (OUT) ── 4 products
    {
        "name": "TeakGarden Reclining Sun Lounger",
        "sku": "HOME-OUT-001",
        "description": (
            "Grade-A teak lounger with five recline positions and UV-resistant Sunbrella cushions included. "
            "Sustainably harvested FSC-certified teak develops a beautiful silver patina over seasons. "
            "Folds flat for compact winter storage; hardware is marine-grade 316 stainless steel."
        ),
        "price": Decimal("549.99"),
        "weight_kg": Decimal("12.000"),
        "category_prefix": "OUT",
        "is_active": True,
    },
    {
        "name": "CompostMaster Tumbler 80L",
        "sku": "HOME-OUT-002",
        "description": (
            "Dual-chamber rotating composter produces finished organic compost in just 2-3 weeks. "
            "Powder-coated steel frame with UV-stabilized recycled plastic body withstands all seasons. "
            "Aeration holes and internal mixing paddles dramatically speed up the decomposition process."
        ),
        "price": Decimal("129.99"),
        "weight_kg": Decimal("8.500"),
        "category_prefix": "OUT",
        "is_active": True,
    },
    {
        "name": "AquaFlow Expandable Garden Hose 100ft",
        "sku": "HOME-OUT-003",
        "description": (
            "Triple-layer latex core expands from 35 ft to 100 ft when pressurized and retracts compactly. "
            "Solid brass fittings and 9-pattern spray nozzle included for watering and washing tasks. "
            "Kink-free design rated for 300 PSI; running shoes-safe drainage feature prevents pooling."
        ),
        "price": Decimal("49.99"),
        "weight_kg": Decimal("1.200"),
        "category_prefix": "OUT",
        "is_active": True,
    },
    {
        "name": "SolarPath LED Garden Lights Set of 12",
        "sku": "HOME-OUT-004",
        "description": (
            "Stainless steel solar path lights charge all day and illuminate automatically dusk to dawn. "
            "Warm 3000 K LED light creates an inviting ambiance along pathways and driveways. "
            "Weatherproof IP65 rating handles heavy rain, snow, and freezing temperatures reliably."
        ),
        "price": Decimal("69.99"),
        "weight_kg": Decimal("2.400"),
        "category_prefix": "OUT",
        "is_active": True,
    },
    # ── Home & Garden > Decor (DEC) ── 3 products
    {
        "name": "HandThrown Ceramic Vase Set of 3",
        "sku": "HOME-DEC-001",
        "description": (
            "Set of three handcrafted ceramic vases in graduated sizes with organic matte glaze finish. "
            "Each piece is uniquely made by artisan potters using traditional wheel-throwing techniques. "
            "Food-safe glazes make them suitable for fresh-cut flowers and dried botanical arrangements."
        ),
        "price": Decimal("79.99"),
        "weight_kg": Decimal("1.800"),
        "category_prefix": "DEC",
        "is_active": True,
    },
    {
        "name": "Macrame Wall Hanging Large",
        "sku": "HOME-DEC-002",
        "description": (
            "Hand-knotted macrame wall hanging crafted from natural cotton rope in a geometric boho pattern. "
            "Measures 90x120 cm and arrives pre-mounted on a driftwood dowel for instant display. "
            "Perfect for minimalist, Scandinavian, and bohemian interiors as a statement art piece."
        ),
        "price": Decimal("59.99"),
        "weight_kg": Decimal("0.650"),
        "category_prefix": "DEC",
        "is_active": True,
    },
    {
        "name": "Himalayan Salt Lamp with Dimmer Switch",
        "sku": "HOME-DEC-003",
        "description": (
            "Authentic Himalayan pink salt crystal lamp emits a warm amber glow for a relaxing atmosphere. "
            "Adjustable dimmer switch controls brightness from soft night-light to reading lamp intensity. "
            "15 W replacement bulb included with UL-certified cord and weighted non-slip base."
        ),
        "price": Decimal("44.99"),
        "weight_kg": Decimal("3.000"),
        "category_prefix": "DEC",
        "is_active": False,  # inactive – 3 of 5
    },
    # ── Sports > Running (RUN) ── 4 products
    {
        "name": "SwiftStride Pro Running Shoes",
        "sku": "SPRT-RUN-001",
        "description": (
            "SwiftStride Pro running shoes feature a carbon fiber plate and nitrogen-infused foam midsole. "
            "Engineered mesh upper adapts to natural foot swelling during long marathon-distance runs. "
            "Recommended by coaches for half-marathon to ultramarathon performance on road surfaces."
        ),
        "price": Decimal("189.99"),
        "weight_kg": Decimal("0.260"),
        "category_prefix": "RUN",
        "is_active": True,
    },
    {
        "name": "TerraGrip Trail Running Shoes",
        "sku": "SPRT-RUN-002",
        "description": (
            "Aggressive 5 mm lugs provide exceptional grip on muddy trails, wet rocks, and loose gravel. "
            "Rock plate protects against sharp obstacles while maintaining natural ground feel underfoot. "
            "GORE-TEX lining keeps feet dry and warm during stream crossings and rainy trail runs."
        ),
        "price": Decimal("149.99"),
        "weight_kg": Decimal("0.310"),
        "category_prefix": "RUN",
        "is_active": True,
    },
    {
        "name": "AeroFit GPS Running Watch",
        "sku": "SPRT-RUN-003",
        "description": (
            "AeroFit GPS watch tracks pace, distance, elevation, heart rate, and blood oxygen levels. "
            "Built-in route navigation and back-to-start feature for safely exploring new trail systems. "
            "7-day battery life in smartwatch mode extends to 20 hours with full GPS tracking enabled."
        ),
        "price": Decimal("349.99"),
        "weight_kg": Decimal("0.050"),
        "category_prefix": "RUN",
        "is_active": True,
    },
    {
        "name": "DuraFlex Running Compression Socks",
        "sku": "SPRT-RUN-004",
        "description": (
            "Medical-grade 20-30 mmHg compression promotes circulation and reduces muscle fatigue. "
            "Merino wool and nylon blend wicks moisture efficiently and prevents blistering on long runs. "
            "Arch support and cushioned heel reduce impact stress during marathon training blocks."
        ),
        "price": Decimal("19.99"),
        "weight_kg": Decimal("0.080"),
        "category_prefix": "RUN",
        "is_active": True,
    },
    # ── Sports > Cycling (CYC) ── 3 products
    {
        "name": "VeloAce Carbon Road Bike Helmet",
        "sku": "SPRT-CYC-001",
        "description": (
            "MIPS-equipped road cycling helmet weighs just 220 g with 22 aerodynamic ventilation channels. "
            "Koroyd crash-absorbing liner provides superior impact protection versus standard EPS foam. "
            "Integrated rear LED visibility light with USB-C charging for urban commuting and racing."
        ),
        "price": Decimal("219.99"),
        "weight_kg": Decimal("0.220"),
        "category_prefix": "CYC",
        "is_active": True,
    },
    {
        "name": "PowerLink GPS Cycling Computer",
        "sku": "SPRT-CYC-002",
        "description": (
            "Turn-by-turn navigation with Strava Live Segments and ClimbPro grade visualization. "
            "Syncs with ANT+ and Bluetooth power meters, heart rate monitors, and smart trainers. "
            "Sunlight-readable color touchscreen records every metric for post-ride cycling analysis."
        ),
        "price": Decimal("399.99"),
        "weight_kg": Decimal("0.093"),
        "category_prefix": "CYC",
        "is_active": True,
    },
    {
        "name": "OmniGrip Gel Cycling Gloves",
        "sku": "SPRT-CYC-003",
        "description": (
            "Gel-padded cycling gloves absorb road vibration during long rides on rough terrain. "
            "Touchscreen-compatible fingertips allow phone use without removing gloves at traffic stops. "
            "Silicone gripper pattern on the palm provides confident braking control in wet conditions."
        ),
        "price": Decimal("34.99"),
        "weight_kg": Decimal("0.090"),
        "category_prefix": "CYC",
        "is_active": True,
    },
    # ── Sports > Swimming (SWM) ── 3 products
    {
        "name": "TidalFlow Competition Swimsuit",
        "sku": "SPRT-SWM-001",
        "description": (
            "Chlorine-resistant polyester-elastane blend maintains shape and color after 200+ pool sessions. "
            "Compression panels reduce hydrodynamic drag and support core muscles during competitive swimming. "
            "Tested and approved to FINA standards for both open water and indoor pool competition use."
        ),
        "price": Decimal("79.99"),
        "weight_kg": Decimal("0.180"),
        "category_prefix": "SWM",
        "is_active": True,
    },
    {
        "name": "AquaVision Anti-Fog Racing Goggles",
        "sku": "SPRT-SWM-002",
        "description": (
            "Hydrodynamic racing goggles with permanent anti-fog treatment and UV400 lens protection. "
            "Dual silicone gaskets create a watertight seal without leaving pressure marks around the eyes. "
            "Wide-angle lens increases peripheral vision significantly for open water swimming navigation."
        ),
        "price": Decimal("49.99"),
        "weight_kg": Decimal("0.065"),
        "category_prefix": "SWM",
        "is_active": True,
    },
    {
        "name": "FlexPull Swim Training Resistance Band Set",
        "sku": "SPRT-SWM-003",
        "description": (
            "Set of four resistance bands designed for dryland swimming training and shoulder stability. "
            "Latex-free construction suitable for athletes with rubber allergies or sensitive skin. "
            "Includes door anchor and illustrated guide with 20 swimming-specific dryland exercises."
        ),
        "price": Decimal("29.99"),
        "weight_kg": Decimal("0.250"),
        "category_prefix": "SWM",
        "is_active": False,  # inactive – 4 of 5
    },
    # ── Books > Fiction (FCT) ── 3 products
    {
        "name": "The Quantum Cartographer",
        "sku": "BOOK-FCT-001",
        "description": (
            "A sweeping science fiction epic following a cartographer who discovers her maps reshape reality. "
            "Shortlisted for the Hugo Award and praised for intricate world-building and philosophical depth. "
            "Hardcover edition, 487 pages; includes author Q&A and annotated map gallery at the back."
        ),
        "price": Decimal("27.99"),
        "weight_kg": Decimal("0.680"),
        "category_prefix": "FCT",
        "is_active": True,
    },
    {
        "name": "Saltwater Ghosts",
        "sku": "BOOK-FCT-002",
        "description": (
            "A haunting literary novel set on a remote Scottish island where three generations collide. "
            "Women navigate love, loss, and the supernatural tide surrounding their historic coastal home. "
            "Winner of the Women's Prize for Fiction; paperback edition, 312 pages with discussion guide."
        ),
        "price": Decimal("16.99"),
        "weight_kg": Decimal("0.320"),
        "category_prefix": "FCT",
        "is_active": True,
    },
    {
        "name": "Midnight Algorithm",
        "sku": "BOOK-FCT-003",
        "description": (
            "Tech thriller following an ethical AI researcher who uncovers a global election manipulation. "
            "Fast-paced narrative explores surveillance capitalism, digital rights, and whistleblowing. "
            "Paperback, 398 pages; praised by cybersecurity professionals for technical accuracy."
        ),
        "price": Decimal("14.99"),
        "weight_kg": Decimal("0.360"),
        "category_prefix": "FCT",
        "is_active": True,
    },
    # ── Books > Technical (TCH) ── 4 products
    {
        "name": "Distributed Systems Design Patterns",
        "sku": "BOOK-TCH-001",
        "description": (
            "Comprehensive guide to designing resilient distributed systems at web scale. "
            "Covers consensus algorithms, event sourcing, CQRS, and service mesh architecture patterns. "
            "Includes case studies from Netflix, Amazon, and Google engineering teams; hardcover, 620 pages."
        ),
        "price": Decimal("59.99"),
        "weight_kg": Decimal("0.980"),
        "category_prefix": "TCH",
        "is_active": True,
    },
    {
        "name": "Python Performance Engineering",
        "sku": "BOOK-TCH-002",
        "description": (
            "Deep dive into profiling, optimizing, and scaling Python applications for production use. "
            "Uses asyncio, Cython, and C extensions to overcome the GIL and optimize hot code paths. "
            "Covers database query optimization, caching strategies, and memory management; paperback, 480 pages."
        ),
        "price": Decimal("49.99"),
        "weight_kg": Decimal("0.720"),
        "category_prefix": "TCH",
        "is_active": True,
    },
    {
        "name": "Kubernetes Security Hardening",
        "sku": "BOOK-TCH-003",
        "description": (
            "Practitioner's guide to securing Kubernetes clusters in production enterprise environments. "
            "Covers RBAC, network policies, container image scanning, and secrets management workflows. "
            "Aligns with CIS Benchmark and NIST SP 800-190 compliance frameworks; paperback, 392 pages."
        ),
        "price": Decimal("54.99"),
        "weight_kg": Decimal("0.640"),
        "category_prefix": "TCH",
        "is_active": True,
    },
    {
        "name": "Machine Learning for APIs",
        "sku": "BOOK-TCH-004",
        "description": (
            "Practical guide to integrating machine learning models into REST and GraphQL APIs. "
            "Covers FastAPI model serving, A/B testing frameworks, feature stores, and drift monitoring. "
            "Real-world examples using PyTorch and scikit-learn; paperback, 356 pages with code samples."
        ),
        "price": Decimal("46.99"),
        "weight_kg": Decimal("0.580"),
        "category_prefix": "TCH",
        "is_active": True,
    },
    # ── Books > Business (BIZ) ── 3 products
    {
        "name": "The Compound Organization",
        "sku": "BOOK-BIZ-001",
        "description": (
            "Explores how leading tech companies use platform business models to build compounding advantages. "
            "Case studies include Shopify, Stripe, and Figma with actionable frameworks for product leaders. "
            "Hardcover, 304 pages; ideal for founders and executives navigating platform strategy decisions."
        ),
        "price": Decimal("32.99"),
        "weight_kg": Decimal("0.520"),
        "category_prefix": "BIZ",
        "is_active": True,
    },
    {
        "name": "Deep Work in the Age of Distraction",
        "sku": "BOOK-BIZ-002",
        "description": (
            "Updated edition of the productivity classic with new chapters on remote work and AI tools. "
            "Evidence-based techniques for reclaiming focused attention in knowledge work environments. "
            "Digital minimalism strategies for modern organizations; paperback, 288 pages with exercises."
        ),
        "price": Decimal("18.99"),
        "weight_kg": Decimal("0.380"),
        "category_prefix": "BIZ",
        "is_active": False,  # inactive – 5 of 5
    },
    {
        "name": "Zero to Series A: Fundraising Strategies",
        "sku": "BOOK-BIZ-003",
        "description": (
            "Written by three VC partners who have reviewed over 10,000 pitch decks combined. "
            "Demystifies the fundraising process for first-time founders from pre-seed through Series A. "
            "Includes pitch deck templates, valuation frameworks, and red flags that kill term sheets; paperback, 256 pages."
        ),
        "price": Decimal("24.99"),
        "weight_kg": Decimal("0.420"),
        "category_prefix": "BIZ",
        "is_active": True,
    },
]


# ---------------------------------------------------------------------------
# Warehouses: 3 distribution centres
# ---------------------------------------------------------------------------

WAREHOUSES: list[dict[str, Any]] = [
    {"name": "East Coast Hub", "location": "New York, NY", "capacity": 10000},
    {"name": "West Coast Hub", "location": "Los Angeles, CA", "capacity": 8000},
    {"name": "Central Warehouse", "location": "Chicago, IL", "capacity": 12000},
]

# SKUs where the first warehouse should have quantity < min_threshold (alerts testing)
BELOW_THRESHOLD_SKUS: frozenset[str] = frozenset(
    {
        "ELEC-SMT-001",
        "ELEC-LAP-003",
        "ELEC-ACC-002",
        "SPRT-RUN-001",
        "SPRT-CYC-001",
        "SPRT-SWM-001",
        "HOME-KIT-002",
        "HOME-OUT-001",
        "CLTH-WMN-002",
        "BOOK-TCH-001",
    }
)

# ---------------------------------------------------------------------------
# Transfer specs: 20 transfers over the past 30 days
# ---------------------------------------------------------------------------

TRANSFER_SPECS: list[dict[str, Any]] = [
    {
        "sku": "ELEC-SMT-001",
        "from_wh": "West Coast Hub",
        "to_wh": "East Coast Hub",
        "qty": 25,
        "days_ago": 29,
        "notes": "Replenishing East Coast smartphone inventory ahead of spring promotional campaign.",
    },
    {
        "sku": "ELEC-LAP-001",
        "from_wh": "Central Warehouse",
        "to_wh": "East Coast Hub",
        "qty": 10,
        "days_ago": 27,
        "notes": "Balancing laptop stock levels across distribution centres.",
    },
    {
        "sku": "SPRT-RUN-001",
        "from_wh": "East Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 30,
        "days_ago": 25,
        "notes": "Redistributing running shoe inventory to support Midwest demand.",
    },
    {
        "sku": "HOME-KIT-002",
        "from_wh": "West Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 15,
        "days_ago": 24,
        "notes": "Transferring blender stock to fulfil Central region backorders.",
    },
    {
        "sku": "CLTH-WMN-002",
        "from_wh": "East Coast Hub",
        "to_wh": "West Coast Hub",
        "qty": 8,
        "days_ago": 22,
        "notes": "Rebalancing cashmere sweater stock ahead of West Coast retail season.",
    },
    {
        "sku": "BOOK-TCH-001",
        "from_wh": "Central Warehouse",
        "to_wh": "West Coast Hub",
        "qty": 20,
        "days_ago": 21,
        "notes": "Moving technical books to West Coast hub for fulfilment efficiency.",
    },
    {
        "sku": "ELEC-ACC-002",
        "from_wh": "Central Warehouse",
        "to_wh": "East Coast Hub",
        "qty": 12,
        "days_ago": 20,
        "notes": "Restocking East Coast monitor inventory following high-volume B2B order.",
    },
    {
        "sku": "SPRT-CYC-001",
        "from_wh": "West Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 18,
        "days_ago": 18,
        "notes": "Cycling helmet transfer to support Midwest cycling event partnerships.",
    },
    {
        "sku": "HOME-OUT-001",
        "from_wh": "East Coast Hub",
        "to_wh": "West Coast Hub",
        "qty": 6,
        "days_ago": 17,
        "notes": "Moving garden furniture to West Coast for summer season preparation.",
    },
    {
        "sku": "ELEC-LAP-003",
        "from_wh": "West Coast Hub",
        "to_wh": "East Coast Hub",
        "qty": 5,
        "days_ago": 15,
        "notes": "Gaming laptop restock for East Coast e-sports retail partners.",
    },
    {
        "sku": "CLTH-MEN-001",
        "from_wh": "East Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 35,
        "days_ago": 14,
        "notes": "Distributing merino wool hoodies to support nationwide retail push.",
    },
    {
        "sku": "SPRT-SWM-001",
        "from_wh": "Central Warehouse",
        "to_wh": "West Coast Hub",
        "qty": 22,
        "days_ago": 13,
        "notes": "Transferring swimwear inventory ahead of West Coast swim season.",
    },
    {
        "sku": "HOME-KIT-003",
        "from_wh": "West Coast Hub",
        "to_wh": "East Coast Hub",
        "qty": 14,
        "days_ago": 12,
        "notes": "Rebalancing Dutch oven stock to meet East Coast chef retail demand.",
    },
    {
        "sku": "BOOK-BIZ-001",
        "from_wh": "East Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 40,
        "days_ago": 10,
        "notes": "Moving business books to Central hub for national corporate sales programme.",
    },
    {
        "sku": "ELEC-SMT-002",
        "from_wh": "Central Warehouse",
        "to_wh": "West Coast Hub",
        "qty": 50,
        "days_ago": 9,
        "notes": "BrightStar Lite 8 transfer to West Coast ahead of carrier promotion launch.",
    },
    {
        "sku": "SPRT-RUN-003",
        "from_wh": "West Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 15,
        "days_ago": 8,
        "notes": "GPS watch inventory redistribution following regional fitness expo.",
    },
    {
        "sku": "CLTH-KDS-001",
        "from_wh": "East Coast Hub",
        "to_wh": "West Coast Hub",
        "qty": 28,
        "days_ago": 6,
        "notes": "Redistributing kids waterproof jackets for West Coast rainy season.",
    },
    {
        "sku": "HOME-DEC-001",
        "from_wh": "Central Warehouse",
        "to_wh": "East Coast Hub",
        "qty": 16,
        "days_ago": 5,
        "notes": "Ceramic vase set transfer for East Coast home decor boutique orders.",
    },
    {
        "sku": "ELEC-ACC-001",
        "from_wh": "West Coast Hub",
        "to_wh": "Central Warehouse",
        "qty": 45,
        "days_ago": 3,
        "notes": "ProSound earbuds restock to meet Central region holiday pre-orders.",
    },
    {
        "sku": "BOOK-FCT-001",
        "from_wh": "East Coast Hub",
        "to_wh": "West Coast Hub",
        "qty": 30,
        "days_ago": 1,
        "notes": "Moving fiction titles to West Coast ahead of book club season.",
    },
]

# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


async def seed_admin_user(session: AsyncSession) -> User:
    """Create the demo admin user if it doesn't already exist."""
    result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
    existing = result.scalar_one_or_none()
    if existing is not None:
        print(f"  ✓ Admin user already exists: {ADMIN_EMAIL}")
        return existing

    user = User(
        id=uuid.uuid4(),
        email=ADMIN_EMAIL,
        name=ADMIN_NAME,
        password_hash=hash_password(ADMIN_PASSWORD),
        role=ADMIN_ROLE,
        api_key_hash=hash_api_key(ADMIN_API_KEY),
        api_key_prefix=get_api_key_prefix(ADMIN_API_KEY),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    print(f"  ✓ Created admin user: {ADMIN_EMAIL}")
    return user


async def seed_categories(session: AsyncSession) -> dict[str, Category]:
    """Create categories idempotently.  Returns a mapping of prefix -> Category."""
    category_map: dict[str, Category] = {}

    for parent_data in CATEGORY_TREE:
        # Check whether the top-level category already exists.
        result = await session.execute(
            select(Category)
            .where(Category.name == parent_data["name"])
            .where(Category.parent_id.is_(None))
        )
        parent = result.scalar_one_or_none()

        if parent is None:
            parent = Category(
                id=uuid.uuid4(),
                name=parent_data["name"],
                description=parent_data["description"],
                parent_id=None,
            )
            session.add(parent)
            await session.flush()
            print(f"  ✓ Created category: {parent_data['name']}")
        else:
            print(f"  ✓ Category already exists: {parent_data['name']}")

        category_map[parent_data["prefix"]] = parent

        for child_data in parent_data.get("children", []):
            child_result = await session.execute(
                select(Category)
                .where(Category.name == child_data["name"])
                .where(Category.parent_id == parent.id)
            )
            child = child_result.scalar_one_or_none()

            if child is None:
                child = Category(
                    id=uuid.uuid4(),
                    name=child_data["name"],
                    description=child_data["description"],
                    parent_id=parent.id,
                )
                session.add(child)
                await session.flush()
                print(f"  ✓ Created subcategory: {child_data['name']}")
            else:
                print(f"  ✓ Subcategory already exists: {child_data['name']}")

            category_map[child_data["prefix"]] = child

    return category_map


async def seed_products(session: AsyncSession, category_map: dict[str, Category]) -> None:
    """Create products idempotently (checked by SKU)."""
    for product_data in PRODUCTS:
        result = await session.execute(select(Product).where(Product.sku == product_data["sku"]))
        if result.scalar_one_or_none() is not None:
            print(f"  ✓ Product already exists: {product_data['sku']}")
            continue

        cat_prefix: str = product_data["category_prefix"]
        category = category_map.get(cat_prefix)
        if category is None:
            print(
                f"  ✗ Category not found for prefix: {cat_prefix} — skipping {product_data['sku']}"
            )
            continue

        product = Product(
            id=uuid.uuid4(),
            name=product_data["name"],
            sku=product_data["sku"],
            description=product_data["description"],
            price=product_data["price"],
            weight_kg=product_data["weight_kg"],
            category_id=category.id,
            is_active=product_data["is_active"],
        )
        session.add(product)
        print(f"  ✓ Created product: {product_data['sku']} – {product_data['name']}")

    await session.flush()


def _det_int(seed_str: str, lo: int, hi: int) -> int:
    """Return a deterministic int in [lo, hi] derived from seed_str via SHA-256."""
    h = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


async def seed_warehouses(session: AsyncSession) -> list[Warehouse]:
    """Create 3 demo warehouses idempotently (checked by name)."""
    result_list: list[Warehouse] = []
    for wh_data in WAREHOUSES:
        result = await session.execute(select(Warehouse).where(Warehouse.name == wh_data["name"]))
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"  ✓ Warehouse already exists: {wh_data['name']}")
            result_list.append(existing)
        else:
            wh = Warehouse(
                id=uuid.uuid4(),
                name=wh_data["name"],
                location=wh_data["location"],
                capacity=wh_data["capacity"],
                is_active=True,
            )
            session.add(wh)
            await session.flush()
            print(f"  ✓ Created warehouse: {wh_data['name']}")
            result_list.append(wh)
    return result_list


async def seed_stock_levels(session: AsyncSession, warehouses: list[Warehouse]) -> None:
    """Create stock levels for all 50 products × 3 warehouses = 150 records.

    Idempotent per (product_id, warehouse_id).  At least 10 products have
    quantity < min_threshold in their first warehouse for low-stock alerts testing.
    """
    products_result = await session.execute(select(Product).order_by(Product.sku))
    products = list(products_result.scalars().all())

    created = 0
    skipped = 0
    for product in products:
        for wh_idx, warehouse in enumerate(warehouses):
            check = await session.execute(
                select(StockLevel).where(
                    StockLevel.product_id == product.id,
                    StockLevel.warehouse_id == warehouse.id,
                )
            )
            if check.scalar_one_or_none() is not None:
                skipped += 1
                continue

            seed_key = f"{product.sku}:{warehouse.name}"
            if product.sku in BELOW_THRESHOLD_SKUS and wh_idx == 0:
                # Force a below-threshold state so low-stock alerts can be tested
                quantity = _det_int(seed_key + ":low_qty", 0, 8)
                min_threshold = _det_int(seed_key + ":thr", 15, 30)
            else:
                quantity = _det_int(seed_key + ":qty", 20, 500)
                min_threshold = _det_int(seed_key + ":thr", 5, 50)

            stock = StockLevel(
                id=uuid.uuid4(),
                product_id=product.id,
                warehouse_id=warehouse.id,
                quantity=quantity,
                min_threshold=min_threshold,
            )
            session.add(stock)
            created += 1

    await session.flush()
    print(f"  ✓ Created {created} stock levels ({skipped} already existed)")


async def seed_transfers(
    session: AsyncSession,
    admin_user: User,
    warehouses: list[Warehouse],
) -> None:
    """Create 20 stock transfers over the past 30 days, idempotent by count."""
    count_result = await session.execute(
        select(func.count(StockTransfer.id)).where(StockTransfer.initiated_by == admin_user.id)
    )
    if (count_result.scalar() or 0) >= 20:
        print("  ✓ Stock transfers already seeded")
        return

    products_result = await session.execute(select(Product).order_by(Product.sku))
    products_by_sku = {p.sku: p for p in products_result.scalars().all()}
    warehouses_by_name = {wh.name: wh for wh in warehouses}

    now = datetime.datetime.now(datetime.UTC)
    created = 0
    for spec in TRANSFER_SPECS:
        product = products_by_sku.get(spec["sku"])
        from_wh = warehouses_by_name.get(spec["from_wh"])
        to_wh = warehouses_by_name.get(spec["to_wh"])
        if not product or not from_wh or not to_wh:
            print(f"  ✗ Skipping transfer – missing reference for: {spec['sku']}")
            continue

        ts = now - datetime.timedelta(days=spec["days_ago"])
        transfer = StockTransfer(
            id=uuid.uuid4(),
            product_id=product.id,
            from_warehouse_id=from_wh.id,
            to_warehouse_id=to_wh.id,
            quantity=spec["qty"],
            initiated_by=admin_user.id,
            notes=spec["notes"],
            created_at=ts,
            updated_at=ts,
        )
        session.add(transfer)
        created += 1

    await session.flush()
    print(f"  ✓ Created {created} stock transfers")


async def seed_audit_logs(
    session: AsyncSession,
    admin_user: User,
    warehouses: list[Warehouse],
) -> None:
    """Create 50 audit log entries with realistic timestamps and JSONB diffs, idempotent by count."""
    count_result = await session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.user_id == admin_user.id)
    )
    if (count_result.scalar() or 0) >= 50:
        print("  ✓ Audit log entries already seeded")
        return

    products_result = await session.execute(select(Product).order_by(Product.sku))
    products = list(products_result.scalars().all())

    categories_result = await session.execute(
        select(Category).where(Category.parent_id.isnot(None)).order_by(Category.name)
    )
    categories = list(categories_result.scalars().all())

    now = datetime.datetime.now(datetime.UTC)
    entries: list[AuditLog] = []

    def log(
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        changes: dict[str, object],
        days_ago: int,
        ip: str = "10.0.1.10",
    ) -> AuditLog:
        ts = now - datetime.timedelta(days=days_ago)
        return AuditLog(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip,
            created_at=ts,
            updated_at=ts,
        )

    # 10 product creates (days 89→71)
    for i, p in enumerate(products[:10]):
        entries.append(
            log(
                "create",
                "product",
                p.id,
                {
                    "created": {
                        "name": p.name,
                        "sku": p.sku,
                        "price": str(p.price),
                        "is_active": True,
                    }
                },
                days_ago=89 - i * 2,
                ip="10.0.1.15",
            )
        )

    # 10 product price updates (days 70→52)
    for i, p in enumerate(products[10:20]):
        old = round(float(p.price) * 0.92, 2)
        entries.append(
            log(
                "update",
                "product",
                p.id,
                {"before": {"price": f"{old:.2f}"}, "after": {"price": str(p.price)}},
                days_ago=70 - i * 2,
                ip="10.0.2.5",
            )
        )

    # 5 product status updates (days 50→46)
    for i, p in enumerate(products[20:25]):
        entries.append(
            log(
                "update",
                "product",
                p.id,
                {"before": {"is_active": not p.is_active}, "after": {"is_active": p.is_active}},
                days_ago=50 - i,
                ip="10.0.1.20",
            )
        )

    # 3 warehouse creates (days 120, 115, 110)
    for i, wh in enumerate(warehouses):
        entries.append(
            log(
                "create",
                "warehouse",
                wh.id,
                {
                    "created": {
                        "name": wh.name,
                        "location": wh.location,
                        "capacity": wh.capacity,
                        "is_active": True,
                    }
                },
                days_ago=120 - i * 5,
                ip="192.168.1.1",
            )
        )

    # 4 warehouse capacity updates (days 95→80)
    wh_cap_updates: list[tuple[Warehouse, int, int, int]] = [
        (warehouses[0], 9000, 10000, 95),
        (warehouses[1], 7500, 8000, 90),
        (warehouses[2], 11000, 12000, 85),
        (warehouses[0], 9500, 9000, 80),
    ]
    for wh, old_cap, new_cap, d in wh_cap_updates:
        entries.append(
            log(
                "update",
                "warehouse",
                wh.id,
                {"before": {"capacity": old_cap}, "after": {"capacity": new_cap}},
                days_ago=d,
                ip="192.168.1.1",
            )
        )

    # 6 stock level quantity updates (days 45→25)
    for i, p in enumerate(products[30:36]):
        old_qty = 30 + i * 15
        new_qty = old_qty + 25 + i * 5
        entries.append(
            log(
                "update",
                "stock_level",
                p.id,
                {
                    "before": {"quantity": old_qty, "min_threshold": 10},
                    "after": {"quantity": new_qty, "min_threshold": 10 + i},
                },
                days_ago=45 - i * 4,
                ip="10.0.1.10",
            )
        )

    # 5 stock transfer audit entries (days 25→5)
    transfer_refs: list[tuple[Product, Warehouse, Warehouse, int]] = [
        (products[36], warehouses[0], warehouses[1], 20),
        (products[37], warehouses[1], warehouses[2], 15),
        (products[38], warehouses[2], warehouses[0], 30),
        (products[39], warehouses[0], warehouses[2], 10),
        (products[40], warehouses[1], warehouses[0], 25),
    ]
    for i, (p, from_wh, to_wh, qty) in enumerate(transfer_refs):
        entries.append(
            log(
                "transfer",
                "stock_transfer",
                p.id,
                {
                    "transferred": {
                        "product_sku": p.sku,
                        "from_warehouse": from_wh.name,
                        "to_warehouse": to_wh.name,
                        "quantity": qty,
                    }
                },
                days_ago=25 - i * 5,
                ip="10.0.1.10",
            )
        )

    # 5 category description updates (days 110→90)
    for i, cat in enumerate(categories[:5]):
        entries.append(
            log(
                "update",
                "category",
                cat.id,
                {"before": {"description": None}, "after": {"description": cat.description}},
                days_ago=110 - i * 5,
                ip="10.0.2.1",
            )
        )

    # 2 product delete audit entries (days 40, 38)
    for i, p in enumerate(products[48:50]):
        entries.append(
            log(
                "delete",
                "product",
                p.id,
                {"deleted": {"name": p.name, "sku": p.sku, "reason": "Product line discontinued"}},
                days_ago=40 - i * 2,
                ip="10.0.1.15",
            )
        )

    # Total: 10+10+5+3+4+6+5+5+2 = 50
    for entry in entries:
        session.add(entry)

    await session.flush()
    print(f"  ✓ Created {len(entries)} audit log entries")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    print("ShipAPI Seed Script")
    print("=" * 50)

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session, session.begin():
        print("\n[1/7] Seeding admin user...")
        admin_user = await seed_admin_user(session)

        print("\n[2/7] Seeding categories...")
        category_map = await seed_categories(session)

        print("\n[3/7] Seeding products...")
        await seed_products(session, category_map)

        print("\n[4/7] Seeding warehouses...")
        warehouses = await seed_warehouses(session)

        print("\n[5/7] Seeding stock levels...")
        await seed_stock_levels(session, warehouses)

        print("\n[6/7] Seeding stock transfers...")
        await seed_transfers(session, admin_user, warehouses)

        print("\n[7/7] Seeding audit logs...")
        await seed_audit_logs(session, admin_user, warehouses)

    await engine.dispose()
    print("\n✓ Seed complete!")


if __name__ == "__main__":
    asyncio.run(main())
