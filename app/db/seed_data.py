"""Static catalog content for the seeder.

Pure data only - no database imports - so it can be inspected, diffed or reused
without spinning up a session.  Image URLs follow the picsum.photos seed pattern
(``https://picsum.photos/seed/<slug>-<n>/800/800``) which always resolves, unlike
hand-written Unsplash photo ids.

Prices are in INR.
"""

from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
CATEGORIES: List[Dict] = [
    {
        "name": "Electronics",
        "slug": "electronics",
        "description": "Audio, wearables, laptops and everyday gadgets from brands people actually trust.",
    },
    {
        "name": "Fashion",
        "slug": "fashion",
        "description": "Wardrobe staples and statement pieces, cut from fabrics that survive the wash.",
    },
    {
        "name": "Home & Living",
        "slug": "home-living",
        "description": "Furniture, lighting and soft furnishings that make a rented flat feel like yours.",
    },
    {
        "name": "Beauty",
        "slug": "beauty",
        "description": "Skincare, fragrance and grooming built on ingredients you can pronounce.",
    },
    {
        "name": "Sports & Fitness",
        "slug": "sports-fitness",
        "description": "Gear for the gym, the trail and the 6am run you keep promising yourself.",
    },
    {
        "name": "Books",
        "slug": "books",
        "description": "Fiction, business and design titles worth clearing a shelf for.",
    },
    {
        "name": "Toys & Games",
        "slug": "toys-games",
        "description": "Building sets, board games and puzzles that survive a rainy weekend.",
    },
    {
        "name": "Grocery",
        "slug": "grocery",
        "description": "Coffee, spices, oils and pantry essentials sourced from small Indian producers.",
    },
]


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
# Keys: category (slug), name, brand, price, compare_at, stock, featured, tags, description
PRODUCTS: List[Dict] = [
    # ----------------------------- Electronics -----------------------------
    {
        "category": "electronics",
        "name": "Aurora Pro Wireless Headphones",
        "brand": "Aurora Audio",
        "price": 18999,
        "compare_at": 24999,
        "stock": 64,
        "featured": True,
        "tags": ["headphones", "wireless", "noise-cancelling", "premium"],
        "description": (
            "Forty hours of playback, adaptive noise cancelling that actually hushes a "
            "commute, and memory-foam cups you forget you are wearing. Multipoint "
            "pairing keeps your laptop and phone connected at once, and a ten-minute "
            "charge buys you five more hours."
        ),
    },
    {
        "category": "electronics",
        "name": "Kestrel Buds Air 3",
        "brand": "Kestrel",
        "price": 4499,
        "compare_at": 6999,
        "stock": 132,
        "featured": True,
        "tags": ["earbuds", "bluetooth", "sweat-resistant"],
        "description": (
            "Featherweight buds with a stem that finally sits flush. IPX5 sweat "
            "resistance handles a monsoon jog, transparency mode lets the traffic in "
            "when you need it, and the case tops up over USB-C in under an hour."
        ),
    },
    {
        "category": "electronics",
        "name": "Meridian 14 Ultrabook",
        "brand": "Meridian",
        "price": 89999,
        "compare_at": 104999,
        "stock": 18,
        "featured": True,
        "tags": ["laptop", "ultrabook", "work", "premium"],
        "description": (
            "A 14-inch 2.8K display in a 1.2kg magnesium chassis. Sixteen gigabytes of "
            "memory and a fast NVMe drive keep thirty browser tabs and a build running "
            "at once, and the fans stay quiet doing it."
        ),
    },
    {
        "category": "electronics",
        "name": "Pulse Fit Smartwatch S2",
        "brand": "Pulse",
        "price": 7999,
        "compare_at": 11999,
        "stock": 87,
        "featured": False,
        "tags": ["smartwatch", "fitness", "heart-rate"],
        "description": (
            "An always-on AMOLED face, seven-day battery and continuous heart-rate and "
            "SpO2 tracking. Over a hundred workout modes, sleep staging that is actually "
            "readable in the morning, and 5ATM water resistance for the pool."
        ),
    },
    {
        "category": "electronics",
        "name": "Volt 65W GaN Charger",
        "brand": "Volt",
        "price": 2299,
        "compare_at": 3199,
        "stock": 210,
        "featured": False,
        "tags": ["charger", "usb-c", "travel", "gan"],
        "description": (
            "Three ports, 65 watts, and a body barely larger than a matchbox thanks to "
            "gallium nitride. Charges a laptop, a phone and a pair of buds at once, with "
            "folding pins that will not shred your bag lining."
        ),
    },
    {
        "category": "electronics",
        "name": "Lumen 4K Streaming Projector",
        "brand": "Lumen",
        "price": 34999,
        "compare_at": None,
        "stock": 12,
        "featured": False,
        "tags": ["projector", "4k", "home-cinema"],
        "description": (
            "Throws a crisp 120-inch image from three metres, with autofocus and keystone "
            "correction that square the picture in seconds. Built-in streaming apps and a "
            "pair of 10W speakers mean no extra boxes on the shelf."
        ),
    },
    {
        "category": "electronics",
        "name": "Nimbus Mechanical Keyboard 75",
        "brand": "Nimbus",
        "price": 6499,
        "compare_at": 8499,
        "stock": 3,
        "featured": False,
        "tags": ["keyboard", "mechanical", "hot-swap", "rgb"],
        "description": (
            "A 75% layout with a gasket mount, hot-swap sockets and pre-lubed tactile "
            "switches. Sounds deep rather than clacky, connects over Bluetooth, 2.4GHz or "
            "cable, and the knob does volume until you remap it."
        ),
    },
    {
        "category": "electronics",
        "name": "Orbit Power Bank 20000",
        "brand": "Orbit",
        "price": 3499,
        "compare_at": 4499,
        "stock": 96,
        "featured": False,
        "tags": ["power-bank", "travel", "fast-charge"],
        "description": (
            "Twenty thousand milliamp hours with 22.5W output, so it refills a phone three "
            "times or tops up a laptop in a pinch. A small display shows the exact "
            "percentage left instead of four vague dots."
        ),
    },
    # ------------------------------- Fashion --------------------------------
    {
        "category": "fashion",
        "name": "Atlas Merino Crew Sweater",
        "brand": "Atlas & Co",
        "price": 4999,
        "compare_at": 7499,
        "stock": 54,
        "featured": True,
        "tags": ["sweater", "merino", "winter", "unisex"],
        "description": (
            "Spun from fine-gauge merino that regulates temperature instead of trapping "
            "heat. Holds its shape through a season of wear, resists odour between washes, "
            "and layers under a jacket without bulk."
        ),
    },
    {
        "category": "fashion",
        "name": "Rove Selvedge Denim Jacket",
        "brand": "Rove",
        "price": 6299,
        "compare_at": None,
        "stock": 37,
        "featured": False,
        "tags": ["jacket", "denim", "selvedge"],
        "description": (
            "Fourteen-ounce raw selvedge that fades to your own creases over a year. "
            "Copper rivets, chain-stitched hem and a slightly dropped shoulder so it sits "
            "well over a hoodie."
        ),
    },
    {
        "category": "fashion",
        "name": "Linen Weekend Shirt",
        "brand": "Cove",
        "price": 2799,
        "compare_at": 3999,
        "stock": 118,
        "featured": False,
        "tags": ["shirt", "linen", "summer", "breathable"],
        "description": (
            "Pure European linen, garment-washed so it arrives soft rather than stiff. "
            "Breathes through a Chennai afternoon, and the relaxed camp collar looks "
            "deliberate untucked."
        ),
    },
    {
        "category": "fashion",
        "name": "Trailhead Canvas Sneakers",
        "brand": "Trailhead",
        "price": 3499,
        "compare_at": 4999,
        "stock": 72,
        "featured": True,
        "tags": ["sneakers", "canvas", "everyday"],
        "description": (
            "Heavy cotton canvas over a vulcanised rubber sole with a cushioned insole "
            "that survives a full day on your feet. Cleans up with a brush and holds its "
            "shape after a soaking."
        ),
    },
    {
        "category": "fashion",
        "name": "Nomad Leather Weekender",
        "brand": "Nomad Goods",
        "price": 8999,
        "compare_at": 12999,
        "stock": 21,
        "featured": False,
        "tags": ["bag", "leather", "travel", "premium"],
        "description": (
            "Full-grain leather that scuffs into a patina, with a waxed-cotton lining and "
            "a separate shoe compartment. Fits two days of clothes and slides over a "
            "trolley handle."
        ),
    },
    {
        "category": "fashion",
        "name": "Solstice Polarised Sunglasses",
        "brand": "Solstice",
        "price": 2499,
        "compare_at": 3499,
        "stock": 143,
        "featured": False,
        "tags": ["sunglasses", "polarised", "uv400"],
        "description": (
            "Polarised UV400 lenses in a lightweight acetate frame, with spring hinges "
            "that forgive being shoved into a bag. Cuts windscreen glare on a highway "
            "drive without darkening everything else."
        ),
    },
    {
        "category": "fashion",
        "name": "Everyday Chino Trousers",
        "brand": "Cove",
        "price": 2999,
        "compare_at": None,
        "stock": 88,
        "featured": False,
        "tags": ["trousers", "chinos", "cotton", "stretch"],
        "description": (
            "Cotton twill with two percent elastane, so they move without going baggy at "
            "the knee. A tapered leg that works with both sneakers and leather, and a "
            "waistband that does not dig in after lunch."
        ),
    },
    {
        "category": "fashion",
        "name": "Kalinga Handloom Silk Scarf",
        "brand": "Kalinga",
        "price": 1899,
        "compare_at": 2699,
        "stock": 5,
        "featured": False,
        "tags": ["scarf", "silk", "handloom", "gift"],
        "description": (
            "Woven on a pit loom in Odisha from mulberry silk, each piece taking a weaver "
            "close to two days. The dye is natural, so no two scarves land on exactly the "
            "same shade."
        ),
    },
    # ---------------------------- Home & Living -----------------------------
    {
        "category": "home-living",
        "name": "Meridian Linen Sofa Cover",
        "brand": "Meridian Home",
        "price": 3299,
        "compare_at": 4599,
        "stock": 46,
        "featured": False,
        "tags": ["sofa", "linen", "washable", "living-room"],
        "description": (
            "A stretch linen blend that grips the frame instead of sliding off every time "
            "someone sits down. Machine washable at 30 degrees, which matters more than "
            "you think with a cat in the house."
        ),
    },
    {
        "category": "home-living",
        "name": "Halo Arc Floor Lamp",
        "brand": "Halo",
        "price": 7499,
        "compare_at": 9999,
        "stock": 24,
        "featured": True,
        "tags": ["lamp", "lighting", "living-room", "dimmable"],
        "description": (
            "A brushed-brass arc that reaches over a sofa without a table underneath it. "
            "Stepless dimming down to a warm 2200K, and a marble base heavy enough that "
            "nobody knocks it over."
        ),
    },
    {
        "category": "home-living",
        "name": "Terra Stoneware Dinner Set",
        "brand": "Terra",
        "price": 4899,
        "compare_at": 6499,
        "stock": 33,
        "featured": False,
        "tags": ["dinnerware", "stoneware", "kitchen", "set-of-16"],
        "description": (
            "Sixteen pieces of reactive-glaze stoneware, kiln-fired so every plate carries "
            "a slightly different pool of colour. Dishwasher and microwave safe, and heavy "
            "enough not to skate across a table."
        ),
    },
    {
        "category": "home-living",
        "name": "Cloudrest Memory Foam Pillow",
        "brand": "Cloudrest",
        "price": 1999,
        "compare_at": 2999,
        "stock": 165,
        "featured": False,
        "tags": ["pillow", "memory-foam", "bedroom", "sleep"],
        "description": (
            "Contoured gel-infused foam that supports a side sleeper's neck without going "
            "hot at 3am. The bamboo-blend cover unzips and washes, which the reviews say "
            "is the part that matters."
        ),
    },
    {
        "category": "home-living",
        "name": "Verdant Ceramic Planter Trio",
        "brand": "Verdant",
        "price": 1499,
        "compare_at": None,
        "stock": 128,
        "featured": False,
        "tags": ["planter", "ceramic", "indoor", "set-of-3"],
        "description": (
            "Three matte-glazed planters in graduated sizes, each with a drainage hole and "
            "a matching saucer, so a repotted monstera does not leave a ring on the "
            "floorboards."
        ),
    },
    {
        "category": "home-living",
        "name": "Anchor Solid Wood Bookshelf",
        "brand": "Anchor",
        "price": 12999,
        "compare_at": 16999,
        "stock": 9,
        "featured": True,
        "tags": ["bookshelf", "wood", "storage", "sheesham"],
        "description": (
            "Five shelves of solid sheesham with a hand-rubbed oil finish and mortise-and-"
            "tenon joints rather than cam locks. Holds a serious book collection without "
            "the middle shelf bowing."
        ),
    },
    {
        "category": "home-living",
        "name": "Ember Scented Soy Candle",
        "brand": "Ember",
        "price": 899,
        "compare_at": 1299,
        "stock": 240,
        "featured": False,
        "tags": ["candle", "soy", "fragrance", "gift"],
        "description": (
            "Sandalwood, cardamom and a little smoke, poured into soy wax with a cotton "
            "wick that burns clean for about fifty hours. The glass is worth keeping once "
            "the wax is gone."
        ),
    },
    {
        "category": "home-living",
        "name": "Brew Master Pour-Over Kettle",
        "brand": "Brew Master",
        "price": 3799,
        "compare_at": 4999,
        "stock": 41,
        "featured": False,
        "tags": ["kettle", "coffee", "gooseneck", "kitchen"],
        "description": (
            "A gooseneck spout that pours a pencil-thin stream, variable temperature from "
            "60 to 100 degrees, and a hold function that keeps the water there for an "
            "hour while you grind."
        ),
    },
    # -------------------------------- Beauty --------------------------------
    {
        "category": "beauty",
        "name": "Lush Vitamin C Serum",
        "brand": "Lush Lab",
        "price": 1299,
        "compare_at": 1899,
        "stock": 187,
        "featured": True,
        "tags": ["serum", "vitamin-c", "skincare", "brightening"],
        "description": (
            "Ten percent stabilised vitamin C with ferulic acid and vitamin E, in an "
            "amber pump bottle that keeps light out. Absorbs without tack, so sunscreen "
            "goes on straight over the top."
        ),
    },
    {
        "category": "beauty",
        "name": "Silk Route Argan Hair Oil",
        "brand": "Silk Route",
        "price": 899,
        "compare_at": None,
        "stock": 154,
        "featured": False,
        "tags": ["hair", "argan", "oil", "frizz"],
        "description": (
            "Cold-pressed Moroccan argan blended with jojoba, light enough that two drops "
            "tame frizz without leaving hair greasy by evening. No added silicones or "
            "synthetic fragrance."
        ),
    },
    {
        "category": "beauty",
        "name": "Noir Eau de Parfum 50ml",
        "brand": "Maison Noir",
        "price": 5499,
        "compare_at": 7999,
        "stock": 28,
        "featured": True,
        "tags": ["perfume", "fragrance", "unisex", "premium"],
        "description": (
            "Bergamot and pink pepper up top, settling into leather, vetiver and a dry "
            "amber base. An eau de parfum concentration, so it stays on skin for the whole "
            "working day rather than the first meeting."
        ),
    },
    {
        "category": "beauty",
        "name": "Clay & Co Purifying Mask",
        "brand": "Clay & Co",
        "price": 749,
        "compare_at": 1099,
        "stock": 203,
        "featured": False,
        "tags": ["mask", "clay", "skincare", "oily-skin"],
        "description": (
            "Kaolin and bentonite with niacinamide, drawing out congestion in ten minutes "
            "without stripping the skin raw. Rinses off cleanly instead of cracking into "
            "the sink."
        ),
    },
    {
        "category": "beauty",
        "name": "Groom Co Beard Care Kit",
        "brand": "Groom Co",
        "price": 1599,
        "compare_at": 2299,
        "stock": 76,
        "featured": False,
        "tags": ["beard", "grooming", "kit", "gift"],
        "description": (
            "Oil, balm, a boar-bristle brush and a pear-wood comb in a box worth gifting. "
            "The balm holds shape without the crunch, and the oil is unscented if you "
            "already wear a fragrance."
        ),
    },
    {
        "category": "beauty",
        "name": "Aqua Shield SPF 50 Sunscreen",
        "brand": "Aqua Shield",
        "price": 649,
        "compare_at": 899,
        "stock": 231,
        "featured": False,
        "tags": ["sunscreen", "spf50", "skincare", "no-white-cast"],
        "description": (
            "A broad-spectrum SPF 50 PA++++ that finishes matte and leaves no white cast "
            "on Indian skin tones. Water resistant for forty minutes, and it layers under "
            "makeup without pilling."
        ),
    },
    {
        "category": "beauty",
        "name": "Velvet Matte Lipstick Set",
        "brand": "Velvet",
        "price": 1899,
        "compare_at": 2799,
        "stock": 4,
        "featured": False,
        "tags": ["lipstick", "matte", "set-of-4", "makeup"],
        "description": (
            "Four transfer-resistant mattes chosen to work across warm and cool "
            "undertones. Pigmented enough for one pass, with a shea and vitamin E base so "
            "lips do not flake by lunchtime."
        ),
    },
    {
        "category": "beauty",
        "name": "Bloom Rose Water Toner",
        "brand": "Bloom",
        "price": 549,
        "compare_at": None,
        "stock": 178,
        "featured": False,
        "tags": ["toner", "rose-water", "skincare", "alcohol-free"],
        "description": (
            "Steam-distilled Kannauj rose water with glycerin and nothing else worth "
            "listing. Alcohol free, so it calms after cleansing instead of tightening, and "
            "the mist head gives an even spray."
        ),
    },
    # --------------------------- Sports & Fitness ---------------------------
    {
        "category": "sports-fitness",
        "name": "Stride Pro Running Shoes",
        "brand": "Stride",
        "price": 6999,
        "compare_at": 9499,
        "stock": 58,
        "featured": True,
        "tags": ["running", "shoes", "cushioned", "marathon"],
        "description": (
            "A nitrogen-infused foam midsole that returns energy over long distances, "
            "wrapped in an engineered mesh upper that drains after a wet run. Neutral "
            "support, built for 10K to full marathon."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Iron Core Adjustable Dumbbells",
        "brand": "Iron Core",
        "price": 14999,
        "compare_at": 19999,
        "stock": 16,
        "featured": True,
        "tags": ["dumbbells", "home-gym", "adjustable", "strength"],
        "description": (
            "A pair that dials from 2.5 to 24 kilos each, replacing fifteen sets of fixed "
            "weights and most of a spare room. The plates lock with an audible click, so "
            "nothing slides mid-press."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Zen Grip Yoga Mat 6mm",
        "brand": "Zen",
        "price": 2299,
        "compare_at": 3199,
        "stock": 94,
        "featured": False,
        "tags": ["yoga", "mat", "non-slip", "eco"],
        "description": (
            "Six millimetres of natural rubber with a polyurethane top that grips harder "
            "as you sweat. Heavy enough to stay flat from the first unroll, and it does "
            "not smell of chemicals."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Hydra Insulated Bottle 1L",
        "brand": "Hydra",
        "price": 1499,
        "compare_at": 1999,
        "stock": 187,
        "featured": False,
        "tags": ["bottle", "insulated", "steel", "leakproof"],
        "description": (
            "Double-walled 18/8 steel that holds cold for twenty-four hours and hot for "
            "twelve. A genuinely leakproof lid, a wide mouth that takes ice cubes, and a "
            "powder coat that does not chip in a gym bag."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Flexline Resistance Band Set",
        "brand": "Flexline",
        "price": 999,
        "compare_at": 1499,
        "stock": 216,
        "featured": False,
        "tags": ["bands", "resistance", "home-workout", "set-of-5"],
        "description": (
            "Five fabric loops from light to extra heavy, woven rather than latex so they "
            "do not roll up the thigh mid-squat. Comes with a carry pouch and a printed "
            "exercise card."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Summit Trekking Backpack 45L",
        "brand": "Summit",
        "price": 5999,
        "compare_at": 8499,
        "stock": 27,
        "featured": False,
        "tags": ["backpack", "trekking", "hiking", "45l"],
        "description": (
            "Forty-five litres with a ventilated back panel and a hip belt that moves the "
            "load off your shoulders. Rain cover tucked into the base, and enough external "
            "lash points for poles and a mat."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Rally Carbon Badminton Racket",
        "brand": "Rally",
        "price": 3499,
        "compare_at": None,
        "stock": 62,
        "featured": False,
        "tags": ["badminton", "racket", "carbon", "lightweight"],
        "description": (
            "Full graphite at 83 grams with a head-light balance that favours fast net "
            "play. Strung at 24 pounds out of the box and supplied with a full-length "
            "cover."
        ),
    },
    {
        "category": "sports-fitness",
        "name": "Peak Foam Roller",
        "brand": "Peak",
        "price": 1299,
        "compare_at": 1799,
        "stock": 0,
        "featured": False,
        "tags": ["recovery", "foam-roller", "mobility"],
        "description": (
            "A high-density EVA roller with a textured surface that reaches knots a smooth "
            "one skates over. Holds its shape under an 120kg load instead of flattening "
            "after a month."
        ),
    },
    # -------------------------------- Books ---------------------------------
    {
        "category": "books",
        "name": "The Quiet Algorithm",
        "brand": "Harlow Press",
        "price": 599,
        "compare_at": 799,
        "stock": 142,
        "featured": True,
        "tags": ["fiction", "literary", "bestseller"],
        "description": (
            "A novel about a recommendation engineer in Bengaluru who starts recognising "
            "her own life in the outputs. Sharp on work, memory and the small "
            "manipulations we agree to. Paperback, 384 pages."
        ),
    },
    {
        "category": "books",
        "name": "Building Things That Last",
        "brand": "Northwind",
        "price": 749,
        "compare_at": 999,
        "stock": 98,
        "featured": False,
        "tags": ["business", "non-fiction", "strategy"],
        "description": (
            "Twelve case studies of companies that survived their own success, and the "
            "unglamorous operational choices behind each. Light on frameworks, heavy on "
            "what actually happened. Hardcover, 312 pages."
        ),
    },
    {
        "category": "books",
        "name": "Grammar of Interfaces",
        "brand": "Foundry Books",
        "price": 1299,
        "compare_at": 1699,
        "stock": 47,
        "featured": True,
        "tags": ["design", "ux", "reference", "illustrated"],
        "description": (
            "A working designer's reference on layout, type and interaction patterns, with "
            "over four hundred annotated examples. Printed large-format on uncoated stock "
            "so it lies flat on a desk."
        ),
    },
    {
        "category": "books",
        "name": "Monsoon Letters",
        "brand": "Harlow Press",
        "price": 499,
        "compare_at": None,
        "stock": 116,
        "featured": False,
        "tags": ["fiction", "historical", "india"],
        "description": (
            "Kerala, 1947. Two sisters write to each other across a country being redrawn, "
            "and the letters slowly stop matching. Quiet, precise and very hard to put "
            "down. Paperback, 296 pages."
        ),
    },
    {
        "category": "books",
        "name": "The Deep Work Companion",
        "brand": "Northwind",
        "price": 649,
        "compare_at": 899,
        "stock": 133,
        "featured": False,
        "tags": ["productivity", "non-fiction", "self-help"],
        "description": (
            "A practical companion on protecting attention in an open-plan, always-pinged "
            "job. Includes a twelve-week programme and the research behind why most focus "
            "advice fails. Paperback, 248 pages."
        ),
    },
    {
        "category": "books",
        "name": "Atlas of Indian Street Food",
        "brand": "Foundry Books",
        "price": 1899,
        "compare_at": 2499,
        "stock": 2,
        "featured": False,
        "tags": ["cookbook", "food", "photography", "coffee-table"],
        "description": (
            "Two hundred recipes traced city by city, photographed at the stalls they came "
            "from. A genuine coffee-table book that still works in a kitchen, with a "
            "washable jacket."
        ),
    },
    {
        "category": "books",
        "name": "Systems for Beginners",
        "brand": "Northwind",
        "price": 849,
        "compare_at": 1099,
        "stock": 71,
        "featured": False,
        "tags": ["science", "non-fiction", "systems-thinking"],
        "description": (
            "An accessible introduction to feedback loops, stocks and flows, using "
            "examples from traffic, epidemics and household budgets rather than "
            "abstractions. Paperback, 264 pages."
        ),
    },
    {
        "category": "books",
        "name": "Night Shift Stories",
        "brand": "Harlow Press",
        "price": 449,
        "compare_at": 599,
        "stock": 159,
        "featured": False,
        "tags": ["short-stories", "fiction", "anthology"],
        "description": (
            "Eighteen short stories set between midnight and dawn, from writers across "
            "eleven Indian cities. Best read one at a time, which is exactly how the "
            "commute allows."
        ),
    },
    # ----------------------------- Toys & Games -----------------------------
    {
        "category": "toys-games",
        "name": "Blockworks Architect Set 1200",
        "brand": "Blockworks",
        "price": 4999,
        "compare_at": 6999,
        "stock": 43,
        "featured": True,
        "tags": ["building-blocks", "stem", "ages-8+", "1200-pieces"],
        "description": (
            "Twelve hundred precision-moulded bricks with three build guides and enough "
            "spare parts to ignore all of them. Compatible with the major brick systems, "
            "which saves an argument later."
        ),
    },
    {
        "category": "toys-games",
        "name": "Settlers of the Deccan",
        "brand": "Meeple Works",
        "price": 2799,
        "compare_at": 3499,
        "stock": 56,
        "featured": False,
        "tags": ["board-game", "strategy", "3-5-players", "family"],
        "description": (
            "A trade-and-settlement board game for three to five players, running about "
            "ninety minutes. Wooden components, a linen-finish board, and rules a new "
            "group can pick up in one round."
        ),
    },
    {
        "category": "toys-games",
        "name": "Circuit Kids Electronics Lab",
        "brand": "Circuit Kids",
        "price": 3299,
        "compare_at": 4499,
        "stock": 38,
        "featured": True,
        "tags": ["stem", "electronics", "educational", "ages-10+"],
        "description": (
            "Sixty snap-together projects that go from a doorbell to a light-sensing alarm "
            "without a soldering iron. The manual explains why each circuit works, not "
            "just where the pieces go."
        ),
    },
    {
        "category": "toys-games",
        "name": "Puzzle Atlas 1000 Piece",
        "brand": "Puzzle Atlas",
        "price": 999,
        "compare_at": 1399,
        "stock": 124,
        "featured": False,
        "tags": ["jigsaw", "puzzle", "1000-pieces", "adults"],
        "description": (
            "A thousand pieces of a hand-illustrated world map, die-cut so no two shapes "
            "repeat and the false fits stay rare. Thick board that does not fray after a "
            "second attempt."
        ),
    },
    {
        "category": "toys-games",
        "name": "Sky Racer Drone Mini",
        "brand": "Sky Racer",
        "price": 5499,
        "compare_at": 7499,
        "stock": 22,
        "featured": False,
        "tags": ["drone", "remote-control", "camera", "ages-14+"],
        "description": (
            "A palm-sized drone with altitude hold, headless mode and a 1080p camera, "
            "which is the combination that lets a beginner fly it indoors on day one. Two "
            "batteries in the box."
        ),
    },
    {
        "category": "toys-games",
        "name": "Wooden Balance Stacker",
        "brand": "Little Grove",
        "price": 1299,
        "compare_at": None,
        "stock": 91,
        "featured": False,
        "tags": ["wooden", "toddler", "montessori", "ages-3+"],
        "description": (
            "Beech blocks finished with non-toxic water-based paint, in shapes that only "
            "balance if the child works out the order. Rounded edges and no piece small "
            "enough to swallow."
        ),
    },
    {
        "category": "toys-games",
        "name": "Codebreaker Card Game",
        "brand": "Meeple Works",
        "price": 699,
        "compare_at": 999,
        "stock": 168,
        "featured": False,
        "tags": ["card-game", "party", "2-8-players", "quick"],
        "description": (
            "A twenty-minute deduction game for two to eight, with enough bluffing that it "
            "works with both a family and a party. Fits in a jacket pocket, which is where "
            "it will live."
        ),
    },
    {
        "category": "toys-games",
        "name": "Nova Telescope 70mm",
        "brand": "Nova",
        "price": 6499,
        "compare_at": 8999,
        "stock": 14,
        "featured": False,
        "tags": ["telescope", "astronomy", "stem", "beginner"],
        "description": (
            "A 70mm refractor on an altazimuth mount that a child can actually aim. Shows "
            "lunar craters and Jupiter's moons on the first clear night, with two eyepieces "
            "and a red-dot finder included."
        ),
    },
    # ------------------------------- Grocery --------------------------------
    {
        "category": "grocery",
        "name": "Ember Roast Coffee Beans 500g",
        "brand": "Ember Roasters",
        "price": 899,
        "compare_at": 1199,
        "stock": 176,
        "featured": True,
        "tags": ["coffee", "arabica", "single-origin", "chikmagalur"],
        "description": (
            "Single-estate arabica from Chikmagalur, roasted medium-dark for chocolate and "
            "dried fig. Roasted to order and stamped with the date, in a valve bag that "
            "keeps it fresh for six weeks."
        ),
    },
    {
        "category": "grocery",
        "name": "Kerala Cold-Pressed Coconut Oil 1L",
        "brand": "Backwater Farms",
        "price": 649,
        "compare_at": 849,
        "stock": 143,
        "featured": False,
        "tags": ["oil", "cold-pressed", "cooking", "kerala"],
        "description": (
            "Pressed from sun-dried copra within a day of husking, unrefined so it keeps "
            "the smell people actually want. Solid below 24 degrees, which is how you know "
            "nothing was cut into it."
        ),
    },
    {
        "category": "grocery",
        "name": "Himalayan Wild Forest Honey 500g",
        "brand": "Highland Hives",
        "price": 749,
        "compare_at": 999,
        "stock": 88,
        "featured": True,
        "tags": ["honey", "raw", "unfiltered", "himalayan"],
        "description": (
            "Raw and unpasteurised, collected from wild hives in Uttarakhand. Crystallises "
            "in winter, which is the point - warm the jar in water rather than the "
            "microwave and it comes straight back."
        ),
    },
    {
        "category": "grocery",
        "name": "Spice Route Garam Masala 200g",
        "brand": "Spice Route",
        "price": 349,
        "compare_at": None,
        "stock": 214,
        "featured": False,
        "tags": ["spices", "masala", "whole-ground", "cooking"],
        "description": (
            "Whole spices dry-roasted and stone-ground in small batches, with more black "
            "cardamom than the supermarket blends dare. Ground weekly and packed in a "
            "light-proof tin."
        ),
    },
    {
        "category": "grocery",
        "name": "Nilgiri Green Tea 250g",
        "brand": "Nilgiri Leaf",
        "price": 549,
        "compare_at": 749,
        "stock": 132,
        "featured": False,
        "tags": ["tea", "green-tea", "nilgiri", "loose-leaf"],
        "description": (
            "Whole-leaf green tea from a 1,800-metre Nilgiri estate, steamed rather than "
            "pan-fired so it stays grassy instead of turning bitter. Takes three infusions "
            "before it gives up."
        ),
    },
    {
        "category": "grocery",
        "name": "Stone Mill Multigrain Atta 5kg",
        "brand": "Stone Mill",
        "price": 449,
        "compare_at": 599,
        "stock": 197,
        "featured": False,
        "tags": ["atta", "flour", "multigrain", "wholegrain"],
        "description": (
            "Seven grains stone-ground slowly so the bran stays intact and the rotis stay "
            "soft the next morning. No maida, no bleaching, and it is milled the week it "
            "ships."
        ),
    },
    {
        "category": "grocery",
        "name": "Cacao House Dark Chocolate 70%",
        "brand": "Cacao House",
        "price": 399,
        "compare_at": 549,
        "stock": 245,
        "featured": False,
        "tags": ["chocolate", "dark", "bean-to-bar", "vegan"],
        "description": (
            "Bean-to-bar from Idukki cacao, conched for seventy-two hours to lose the "
            "grit. Seventy percent, so it is bitter enough to be interesting and sweet "
            "enough to finish."
        ),
    },
    {
        "category": "grocery",
        "name": "Harvest Mixed Nuts 750g",
        "brand": "Harvest",
        "price": 1099,
        "compare_at": 1499,
        "stock": 1,
        "featured": False,
        "tags": ["nuts", "dry-fruits", "healthy", "snack"],
        "description": (
            "Almonds, cashews, pistachios and walnuts, dry-roasted without oil and lightly "
            "salted. Vacuum-packed in a resealable jar so the last handful is as crisp as "
            "the first."
        ),
    },
]


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
# ``expires_in_days`` of None means the coupon never expires; a negative value
# backdates it, which is how EXPIRED10 stays permanently expired for demos.
COUPONS: List[Dict] = [
    {
        "code": "WELCOME10",
        "type": "percent",
        "value": 10,
        "min_order": 499,
        "max_discount": 300,
        "is_active": True,
        "expires_in_days": 365,
    },
    {
        "code": "NEXA500",
        "type": "flat",
        "value": 500,
        "min_order": 2999,
        "max_discount": None,
        "is_active": True,
        "expires_in_days": 180,
    },
    {
        "code": "FESTIVE25",
        "type": "percent",
        "value": 25,
        "min_order": 1999,
        "max_discount": 1500,
        "is_active": True,
        "expires_in_days": 45,
    },
    {
        "code": "FREESHIP",
        "type": "flat",
        "value": 49,
        "min_order": 0,
        "max_discount": None,
        "is_active": True,
        "expires_in_days": None,
    },
    {
        "code": "BIGSAVE",
        "type": "percent",
        "value": 15,
        "min_order": 4999,
        "max_discount": 2000,
        "is_active": True,
        "expires_in_days": 90,
    },
    {
        "code": "EXPIRED10",
        "type": "percent",
        "value": 10,
        "min_order": 0,
        "max_discount": 200,
        "is_active": True,
        "expires_in_days": -14,
    },
]


# ---------------------------------------------------------------------------
# Extra customers (beyond the two demo accounts in settings)
# ---------------------------------------------------------------------------
CUSTOMERS: List[Dict] = [
    {"name": "Rohan Iyer", "email": "rohan.iyer@example.com", "phone": "9840112233"},
    {"name": "Ananya Nair", "email": "ananya.nair@example.com", "phone": "9840223344"},
    {"name": "Vikram Reddy", "email": "vikram.reddy@example.com", "phone": "9840334455"},
    {"name": "Sneha Kulkarni", "email": "sneha.k@example.com", "phone": "9840445566"},
    {"name": "Arjun Menon", "email": "arjun.menon@example.com", "phone": "9840556677"},
    {"name": "Divya Raghavan", "email": "divya.r@example.com", "phone": "9840667788"},
    {"name": "Karthik Subramanian", "email": "karthik.s@example.com", "phone": "9840778899"},
    {"name": "Meera Joshi", "email": "meera.joshi@example.com", "phone": "9840889900"},
    {"name": "Aditya Bose", "email": "aditya.bose@example.com", "phone": "9840990011"},
    {"name": "Fatima Sheikh", "email": "fatima.sheikh@example.com", "phone": "9841001122"},
    {"name": "Nikhil Verma", "email": "nikhil.verma@example.com", "phone": "9841112233"},
    {"name": "Lakshmi Pillai", "email": "lakshmi.p@example.com", "phone": "9841223344"},
]


# ---------------------------------------------------------------------------
# Review content
# ---------------------------------------------------------------------------
# Grouped by rating so a 5-star review never reads like a complaint.
REVIEW_POOL: Dict[int, List[tuple]] = {
    5: [
        ("Exactly what I hoped for", "Arrived two days early and the quality is better than the photos suggest. No notes."),
        ("Worth every rupee", "I hesitated at this price and I should not have. Six weeks in and it still looks new."),
        ("Buying a second one", "Good enough that I ordered another for my brother. Packaging was solid too."),
        ("Best purchase this year", "Does the one thing I bought it for, and does it properly. Rare these days."),
        ("Genuinely impressed", "The finish is a step above what I expected at this price point. Recommended."),
    ],
    4: [
        ("Very good, one small niggle", "Really happy overall. Took a couple of days to get used to, but no regrets."),
        ("Solid build, slightly pricey", "Quality is not in question. I just think it could be a few hundred cheaper."),
        ("Does the job well", "Nothing flashy, but it works reliably and the finish is neat. Would buy again."),
        ("Good, delivery was slow", "The product is great. Shipping took longer than the estimate said it would."),
        ("Close to perfect", "One design choice I would change, otherwise excellent. Four stars is fair."),
    ],
    3: [
        ("Decent for the price", "It is fine. Not remarkable, not bad. Does what the description says."),
        ("Mixed feelings", "Half of it I love, half of it feels like a compromise. Middle of the road."),
        ("Okay but check the size", "Runs a little different from the chart. Worth measuring before you order."),
        ("Average", "Works, but I have used better for similar money. No complaints about the seller though."),
    ],
    2: [
        ("Not quite what I expected", "The colour is noticeably different from the listing photos. Usable, but disappointing."),
        ("Underwhelming", "It works, but the finish feels cheaper in hand than it looks on screen."),
        ("Needed a return", "Mine had a defect out of the box. Support was helpful, hence two stars not one."),
    ],
    1: [
        ("Stopped working quickly", "Lasted under three weeks before it failed. Would not buy again."),
        ("Not as described", "Several details do not match the listing. Sending it back."),
    ],
}


__all__ = ["CATEGORIES", "PRODUCTS", "COUPONS", "CUSTOMERS", "REVIEW_POOL"]
