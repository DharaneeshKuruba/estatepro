"""
Generates synthetic real-estate documents (as text files) and ingests them into ChromaDB
with role-based metadata for access control.
"""
import os
from pathlib import Path

# ── Document content ─────────────────────────────────────────────────────────

PROPERTY_DOCS = {
    "AG001": [
        {
            "property_id": "P1001", "agent_id": "AG001",
            "title": "Luxury 3BHK Apartment – Whitefield, Bangalore",
            "location": "Whitefield, Bangalore",
            "property_type": "Apartment",
            "amenities": "Pool, Gym, Parking, 24/7 Security, Clubhouse",
            "actual_price": "₹1,20,00,000",
            "quoted_price": "₹1,10,00,000",
            "rental_yield": "4.5%",
            "appreciation": "7% annually",
            "description": (
                "Located in a prime residential enclave in Whitefield, this 3BHK luxury apartment "
                "spans 1,850 sq ft. The building offers world-class amenities including a rooftop pool, "
                "fully equipped gym, and covered parking. Walking distance to ITPL and major tech parks."
            ),
        },
        {
            "property_id": "P1002", "agent_id": "AG001",
            "title": "2BHK Premium Villa – Sarjapur Road, Bangalore",
            "location": "Sarjapur Road, Bangalore",
            "property_type": "Villa",
            "amenities": "Garden, Garage, Solar Panels, CCTV",
            "actual_price": "₹85,00,000",
            "quoted_price": "₹80,00,000",
            "rental_yield": "3.8%",
            "appreciation": "6% annually",
            "description": (
                "A beautifully landscaped 2BHK villa with sustainable solar panels and smart home systems. "
                "Ideal for young families seeking a quiet neighbourhood close to top schools and hospitals."
            ),
        },
    ],
    "AG002": [
        {
            "property_id": "P2001", "agent_id": "AG002",
            "title": "4BHK Penthouse – Bandra, Mumbai",
            "location": "Bandra West, Mumbai",
            "property_type": "Penthouse",
            "amenities": "Private Terrace, Sea View, Heated Pool, Concierge",
            "actual_price": "₹5,50,00,000",
            "quoted_price": "₹5,00,00,000",
            "rental_yield": "3.2%",
            "appreciation": "9% annually",
            "description": (
                "An ultra-luxury penthouse atop a 32-storey tower in Bandra West. "
                "Offers panoramic sea views, a private heated rooftop pool, and 24-hour concierge. "
                "The 4,200 sq ft residence is move-in ready with Italian marble flooring throughout."
            ),
        },
        {
            "property_id": "P2002", "agent_id": "AG002",
            "title": "Studio Apartment – Andheri East, Mumbai",
            "location": "Andheri East, Mumbai",
            "property_type": "Studio",
            "amenities": "Co-working Space, Gym, High-speed WiFi",
            "actual_price": "₹60,00,000",
            "quoted_price": "₹58,00,000",
            "rental_yield": "5.1%",
            "appreciation": "5% annually",
            "description": (
                "A compact, fully furnished studio apartment tailored for working professionals. "
                "Located 10 minutes from Andheri Metro station. High rental demand due to proximity "
                "to SEEPZ, MIDC, and multiple corporate offices."
            ),
        },
    ],
    "AG003": [
        {
            "property_id": "P3001", "agent_id": "AG003",
            "title": "3BHK Independent House – Anna Nagar, Chennai",
            "location": "Anna Nagar, Chennai",
            "property_type": "Independent House",
            "amenities": "Private Garden, Garage, Rainwater Harvesting",
            "actual_price": "₹95,00,000",
            "quoted_price": "₹90,00,000",
            "rental_yield": "4.0%",
            "appreciation": "6.5% annually",
            "description": (
                "A spacious independent house in the heart of Anna Nagar with a private garden "
                "and rainwater harvesting facility. Minutes away from top educational institutions "
                "and commercial markets. An excellent long-term investment."
            ),
        },
    ],
}

MARKET_REPORT = """
REAL ESTATE MARKET REPORT – Q1 2026
=====================================
1. NATIONAL OVERVIEW
   - Residential demand grew 12% YoY across Tier-1 cities.
   - Average appreciation rate: 7.2% nationally.
   - Rental yields remain attractive: 4–5.5% in metro areas.

2. CITY-WISE TRENDS
   Bangalore:
   - IT corridor (Whitefield, Sarjapur) driving demand.
   - 2BHK average price: ₹80–95 lakhs. 3BHK: ₹1.1–1.5 Cr.
   - QoQ price growth: 2.8%.

   Mumbai:
   - Bandra and Andheri remain top investment zones.
   - Luxury segment (₹5Cr+) appreciated 9% YoY.
   - Rental yields in Andheri East: 5%.

   Chennai:
   - Anna Nagar and OMR are high-growth corridors.
   - Mid-segment demand driving 6.5% YoY appreciation.

3. INVESTMENT HOTSPOTS
   - Whitefield, Bangalore (tech-driven demand, 7% YoY).
   - Bandra West, Mumbai (luxury scarcity premium).
   - Anna Nagar, Chennai (stable growth, strong rental market).

4. RISK FACTORS
   - Rising interest rates may soften demand in H2 2026.
   - Regulatory delays in peripheral areas.
   - Oversupply risk in studio segment in Hyderabad.
"""

INVESTMENT_INSIGHTS = """
INVESTMENT INSIGHTS REPORT – REAL ESTATE 2026
===============================================
1. TOP PICKS BY ROI
   - P1001 (Whitefield): ROI 4.5% + 7% appreciation = ~11.5% total return.
   - P2001 (Bandra Penthouse): 3.2% + 9% = ~12.2% total return (premium risk).
   - P2002 (Andheri Studio): 5.1% yield – highest cash-flow play.

2. CRITERIA FOR SELECTION
   - Rental Yield > 4%: Preferred for cash flow investors.
   - Appreciation > 7%: Growth investors targeting wealth creation.
   - Location Score: Proximity to employment hubs, transit, and schools.

3. BUYER SEGMENTS
   - First-time buyers: Prefer 2BHK in ₹60–90L range (Chennai, Bangalore).
   - NRIs: High interest in luxury Mumbai properties (stable USD-INR hedge).
   - Investors: Studio/1BHK in IT corridors for optimal rental income.

4. MARKET OUTLOOK
   - Interest rates expected to ease in Q3 2026 (RBI signals).
   - New supply in luxury segment expected to moderate prices in H2.
   - Recommended: Lock in prices in Tier-1 cities in Q1–Q2 2026.
"""

LEGAL_DOCUMENTS = """
LEGAL & COMPLIANCE OVERVIEW – REAL ESTATE TRANSACTIONS
=======================================================
1. TITLE DEED VERIFICATION
   - All properties P1001, P1002, P2001, P2002, P3001 have clear title deeds.
   - Encumbrance certificates issued within the last 90 days.

2. RERA REGISTRATION
   - Properties in Karnataka (P1001, P1002): RERA-KA-2024-0012, RERA-KA-2024-0018.
   - Properties in Maharashtra (P2001, P2002): RERA-MH-2024-0045, RERA-MH-2024-0046.
   - Properties in Tamil Nadu (P3001): RERA-TN-2024-0033.

3. DUE DILIGENCE CHECKLIST
   ✅ Approved building plan from municipal authority.
   ✅ Completion certificate / Occupancy certificate obtained.
   ✅ No pending litigation on any listed property.
   ✅ Society/association NOC obtained where applicable.

4. TAXATION & STAMP DUTY
   - Karnataka: 5% stamp duty + 1% registration charge.
   - Maharashtra: 6% stamp duty + 1% local body tax.
   - Tamil Nadu: 7% stamp duty + 4% registration fee.

5. LOAN ELIGIBILITY
   - All listed properties are pre-approved by SBI, HDFC, and ICICI.
   - LTV ratio: up to 80% for salaried, 75% for self-employed.
"""

PUBLIC_LISTINGS = """
PUBLIC PROPERTY LISTINGS – BUYER SUMMARY
==========================================
Available Properties (Quoted Prices Only):

1. Luxury 3BHK Apartment – Whitefield, Bangalore
   Quoted Price: ₹1,10,00,000 | Type: Apartment | Amenities: Pool, Gym, Parking

2. 2BHK Premium Villa – Sarjapur Road, Bangalore
   Quoted Price: ₹80,00,000 | Type: Villa | Amenities: Garden, Garage, Solar Panels

3. 4BHK Penthouse – Bandra West, Mumbai
   Quoted Price: ₹5,00,00,000 | Type: Penthouse | Amenities: Sea View, Heated Pool

4. Studio Apartment – Andheri East, Mumbai
   Quoted Price: ₹58,00,000 | Type: Studio | Amenities: Co-working, Gym, WiFi

5. 3BHK Independent House – Anna Nagar, Chennai
   Quoted Price: ₹90,00,000 | Type: Independent House | Amenities: Garden, Garage

To schedule a visit or request more information, contact our registered agents.
"""

MARKET_SUMMARY_BUYER = """
MARKET SUMMARY FOR BUYERS – Q1 2026
=====================================
Key insights for property buyers:

1. Bangalore is the most affordable metro for apartment purchases (₹60L–₹1.5Cr range).
2. Mumbai offers premium luxury options with strong long-term appreciation.
3. Chennai's Anna Nagar area has shown consistent 6–7% annual appreciation.
4. Best time to buy: Q1–Q2 2026 before anticipated rate cuts increase demand.
5. Always verify RERA registration before committing to any purchase.
6. Seek pre-approval for home loans to strengthen negotiating position.
7. Consult a registered agent for arranging property visits and due diligence.
"""


def _property_chunk(p: dict, include_actual: bool = True) -> str:
    lines = [
        f"Property ID: {p['property_id']}",
        f"Agent ID: {p['agent_id']}",
        f"Title: {p['title']}",
        f"Location: {p['location']}",
        f"Property Type: {p['property_type']}",
        f"Amenities: {p['amenities']}",
    ]
    if include_actual:
        lines.append(f"Actual Price: {p['actual_price']}")
    lines += [
        f"Quoted Price: {p['quoted_price']}",
        f"Rental Yield: {p['rental_yield']}",
        f"Appreciation Rate: {p['appreciation']}",
        f"Description: {p['description']}",
    ]
    return "\n".join(lines)


def generate_documents(docs_root: str = "docs") -> dict[str, str]:
    """Return a dict of {relative_path: content} for all synthetic documents."""
    docs: dict[str, str] = {}
    root = Path(docs_root)

    # Admin documents
    admin_dir = root / "admin"
    # All properties (with actual prices)
    all_prop_content = "PROPERTY DOCUMENTS – ALL AGENTS\n" + "=" * 40 + "\n\n"
    for agent_id, properties in PROPERTY_DOCS.items():
        for p in properties:
            all_prop_content += _property_chunk(p, include_actual=True) + "\n\n" + "-" * 40 + "\n\n"
    docs[str(admin_dir / "property_documents_all.txt")] = all_prop_content
    docs[str(admin_dir / "legal_documents.txt")] = LEGAL_DOCUMENTS
    docs[str(admin_dir / "market_reports.txt")] = MARKET_REPORT
    docs[str(admin_dir / "investment_insights.txt")] = INVESTMENT_INSIGHTS

    # Agent documents (each agent sees only their own, with actual price)
    for agent_id, properties in PROPERTY_DOCS.items():
        agent_dir = root / "agent"
        content = f"PROPERTY DOCUMENTS – AGENT {agent_id}\n" + "=" * 40 + "\n\n"
        for p in properties:
            content += _property_chunk(p, include_actual=True) + "\n\n" + "-" * 40 + "\n\n"
        docs[str(agent_dir / f"property_documents_agent_{agent_id}.txt")] = content

    # Buyer documents (only quoted prices)
    buyer_dir = root / "buyer"
    docs[str(buyer_dir / "public_property_listings.txt")] = PUBLIC_LISTINGS
    docs[str(buyer_dir / "market_summary.txt")] = MARKET_SUMMARY_BUYER

    return docs


def write_documents(docs_root: str = "docs"):
    """Write all synthetic documents to disk."""
    docs = generate_documents(docs_root)
    for path_str, content in docs.items():
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"[Docs] Generated {len(docs)} documents under '{docs_root}/'")
    return docs
