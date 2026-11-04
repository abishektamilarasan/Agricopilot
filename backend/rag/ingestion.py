"""
Knowledge Ingestion Pipeline
Ingests agricultural knowledge documents into ChromaDB for RAG retrieval.
Includes a built-in agricultural knowledge corpus.
"""

from rag.knowledge_base import knowledge_base

# ──────────────────────────────────────────────
# Built-in Agricultural Knowledge Corpus
# ──────────────────────────────────────────────

AGRI_KNOWLEDGE = [
    # --- Rice ---
    {
        "id": "rice-management",
        "source": "TNAU-Crop-Guide/Rice",
        "text": """Rice Water & Nutrient Management:
Rice requires 1200-2000mm of water. Alternate Wetting and Drying (AWD) saves 15-30% water. Maintain 2-5cm standing water during tillering/flowering. 
N requirement: 100-150 kg/ha in 3 splits (basal, tillering, panicle initiation). Apply P (40-60 kg/ha) entirely basal. K (40-60 kg/ha) in 2 splits. Apply 25 kg ZnSO4/ha for zinc deficiency (common in flooded soils).
Common Diseases: Blast (diamond lesions) - use tricyclazole. Bacterial Leaf Blight (yellow lesions) - avoid excess N. Brown spot - improve K and Si fertility."""
    },
    # --- Maize ---
    {
        "id": "maize-management",
        "source": "TNAU-Crop-Guide/Maize",
        "text": """Maize Crop Management & Nutrition:
Highly sensitive to drought during tasseling and silking (60-70 days). Needs 150-200 kg N/ha applied in 3 splits (basal, knee-high V6, pre-tassel V12). 
P (60-80 kg/ha) and K (40-60 kg/ha). Interveinal chlorosis indicates Magnesium deficiency. Fall Armyworm (FAW) is a major pest; use Spinetoram or Emamectin benzoate."""
    },
    # --- Millets ---
    {
        "id": "millet-management",
        "source": "TNAU-Crop-Guide/Millets",
        "text": """Millets (Pearl/Finger Millet) Management:
Highly drought-tolerant and climate-resilient. Requires only 250-700mm rainfall. Ideal for Red and sandy soils. Low fertilizer requirement (40-60 kg N/ha).
Finger millet is rich in calcium; Pearl millet in iron. Susceptible to Downy Mildew and Ergot. Harvest when grain hardens."""
    },
    # --- Sugarcane ---
    {
        "id": "sugarcane-management",
        "source": "TNAU-Crop-Guide/Sugarcane",
        "text": """Sugarcane Cultivation & Nutrition:
Long duration crop (10-14 months). High water requirement (2000-2500mm). Best in Alluvial and deep Clay soils with pH 6.5-7.5.
Nutrient heavy: 275-300 kg N/ha, 100 kg P2O5, 120 kg K2O. Apply N and K in 4 equal splits. Early shoot borer and internode borer are major pests. Use Trichogramma egg parasitoids for biological control."""
    },
    # --- Banana ---
    {
        "id": "banana-management",
        "source": "TNAU-Crop-Guide/Banana",
        "text": """Banana Cultivation:
Requires continuous moisture (1800-2500mm/year). Extremely sensitive to waterlogging — requires well-drained soil (Alluvial or Red Loam).
Heavy feeder: 200g N, 50g P, 300g K per plant. Needs propping during bunch development. Panama wilt (Fusarium) and Sigatoka leaf spot are severe diseases. Use disease-free tissue culture plants."""
    },
    # --- Cotton ---
    {
        "id": "cotton-management",
        "source": "TNAU-Crop-Guide/Cotton",
        "text": """Cotton Cultivation:
Thrives in Black Cotton Soils (Vertisols) due to high moisture retention. Deep rooted. Rainfed requires 500-700mm.
Fertilizer: 120 kg N, 60 kg P, 60 kg K/ha. Major pests: Pink Bollworm and Whitefly. Use Bt cotton hybrids to manage bollworms. Avoid waterlogging during seedling and boll opening stages."""
    },
    # --- Groundnut ---
    {
        "id": "groundnut-management",
        "source": "TNAU-Crop-Guide/Groundnut",
        "text": """Groundnut Cultivation:
Best grown in Coastal Sandy Soils or Red Sandy Loam (easy peg penetration and pod development). Avoid heavy clay.
Legume crop — requires rhizobium inoculation. Apply Gypsum (400 kg/ha) at 45 days (flowering) to improve pod filling and oil content. Major pest: Leaf miner. Major disease: Tikka leaf spot."""
    },
    # --- Tomato ---
    {
        "id": "tomato-management",
        "source": "TNAU-Crop-Guide/Tomato",
        "text": """Tomato Cultivation:
Optimal temp 21-24°C; fruit setting fails above 35°C or below 10°C. Requires well-drained Red or Alluvial soils.
High P and K requirement for fruit quality. Blossom End Rot is caused by Calcium deficiency and irregular watering. Whitefly transmits Leaf Curl Virus — manage with yellow sticky traps and imidacloprid."""
    },
    # --- Onion ---
    {
        "id": "onion-management",
        "source": "TNAU-Crop-Guide/Onion",
        "text": """Onion Cultivation:
Shallow rooted crop, requires frequent light irrigation. Needs well-drained loamy soils; highly sensitive to waterlogging.
Sulfur is critical for pungency (apply 20-40 kg S/ha). Thrips and Purple Blotch are major threats. Stop irrigation 10-15 days before harvest for proper bulb curing."""
    },
    # --- Mango ---
    {
        "id": "mango-management",
        "source": "TNAU-Crop-Guide/Mango",
        "text": """Mango Orchard Management:
Highly adaptable but prefers deep, well-drained Laterite or Red soils. Cannot tolerate waterlogging.
Needs dry weather during flowering for fruit set. Apply 1kg N, 1kg P, 1.5kg K per mature tree annually. Mango hopper is the most destructive pest during flowering. Spongy tissue is a physiological disorder in Alphonso."""
    },
    
    # ==========================================
    # Tamil Nadu Soil Profiles (Pros & Cons)
    # ==========================================
    {
        "id": "soil-red",
        "source": "TNAU-Soil-DB/Red-Soil",
        "text": """Red Soil (Alfisol):
Dominant in Tamil Nadu (covering ~62% of the state). Formed from weathering of granites. 
Pros: Excellent drainage, easy to work, good response to fertilizers. Ideal for millets, groundnut, and pulses.
Cons: Poor water retention, low organic matter (<0.5%), generally deficient in Nitrogen, Phosphorus, and Zinc. Prone to erosion."""
    },
    {
        "id": "soil-black",
        "source": "TNAU-Soil-DB/Black-Soil",
        "text": """Black Soil (Vertisol):
Common in Coimbatore, Tirunelveli, and Virudhunagar. Rich in montmorillonite clay.
Pros: Exceptionally high water holding capacity. Highly fertile, rich in Calcium, Potassium, and Magnesium. Best for Cotton, Maize, and Sorghum.
Cons: Poor drainage, swells when wet and cracks deeply when dry. Difficult to plow when wet. Deficient in Nitrogen and Organic Carbon."""
    },
    {
        "id": "soil-alluvial",
        "source": "TNAU-Soil-DB/Alluvial-Soil",
        "text": """Alluvial Soil (Entisol):
Found in the Cauvery delta (Thanjavur, Tiruvarur). River-deposited silt and clay.
Pros: Highly fertile, rich in Potash and Loam. Excellent water retention. The most productive soil for Rice, Sugarcane, and Banana.
Cons: Can suffer from waterlogging and poor drainage in lower reaches. Sometimes deficient in Nitrogen and Phosphorus."""
    },
    {
        "id": "soil-laterite",
        "source": "TNAU-Soil-DB/Laterite-Soil",
        "text": """Laterite Soil:
Found in hilly regions (Nilgiris, Kodaikanal, parts of Kanyakumari). Formed under heavy rainfall.
Pros: Good physical condition, well-drained. Excellent for plantation crops (Tea, Coffee, Rubber) and orchard crops like Mango.
Cons: Highly acidic (pH 4.5-5.5). Severe leaching removes silica and nutrients. Requires regular liming and heavy organic manure. Poor in P and K."""
    },
    {
        "id": "soil-sandy",
        "source": "TNAU-Soil-DB/Coastal-Sandy",
        "text": """Coastal Sandy Soil:
Found along the Coromandel coast.
Pros: Extremely well-drained, very easy root penetration. Excellent for Groundnut, Cashew, and Coconut.
Cons: Extremely poor water holding capacity (requires frequent irrigation). Very low nutrient status. Highly susceptible to leaching of applied fertilizers."""
    },

    # --- General Best Practices ---
    {
        "id": "soil-health",
        "source": "best-practices/soil",
        "text": """Soil Health Management:
Maintain organic carbon >1% (10 g/kg). Apply 5-10 tons/ha FYM or compost annually.
Practice crop rotation — cereal-legume rotation improves soil N. Minimum tillage reduces
erosion and preserves soil structure. Green manuring with dhaincha or sunhemp adds 60-80 kg N/ha.
Soil pH management: lime acidic soils (pH <5.5), apply gypsum to sodic soils (pH >8.5).
Micro-irrigation (drip/sprinkler) improves water use efficiency by 30-50%.
Mulching reduces evaporation by 25-35% and suppresses weeds."""
    },
    {
        "id": "climate-adaptation",
        "source": "best-practices/climate",
        "text": """Climate-Smart Agriculture Practices:
1. Crop diversification — grow multiple crops to spread risk
2. Conservation agriculture — minimum tillage, residue retention, crop rotation
3. Drought-tolerant varieties — use climate-adapted cultivars
4. Rainwater harvesting — farm ponds, check dams, contour bunding
5. Agroforestry — trees provide shade, windbreaks, additional income"""
    }
]


# ──────────────────────────────────────────────
# Ingestion Functions
# ──────────────────────────────────────────────

def ingest_built_in_knowledge():
    """Add the built-in agricultural knowledge to ChromaDB."""
    print("Checking knowledge base...")
    if knowledge_base.collection is None:
        print("Warning: ChromaDB collection not initialized.")
        return

    # Check if we already have documents
    count = knowledge_base.collection.count()
    if count > 0:
        print(f"Knowledge base already contains {count} documents. Skipping built-in ingestion.")
        # But we actually want to force update during development
        print("Forcing update of built-in knowledge...")

    # Prepare data for insertion
    ids = [doc["id"] for doc in AGRI_KNOWLEDGE]
    documents = [doc["text"] for doc in AGRI_KNOWLEDGE]
    metadatas = [{"source": doc["source"]} for doc in AGRI_KNOWLEDGE]

    # Add to ChromaDB
    try:
        knowledge_base.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully ingested {len(AGRI_KNOWLEDGE)} knowledge documents.")
    except Exception as e:
        print(f"Error during ingestion: {e}")


def query_knowledge(query: str, n_results: int = 3) -> str:
    """Query the knowledge base and return a formatted context string."""
    try:
        results = knowledge_base.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            source = results['metadatas'][0][i]['source']
            context_parts.append(f"[{source}]: {doc}")
            
        return "\n\n".join(context_parts)
    except Exception as e:
        print(f"Error querying knowledge base: {e}")
        return ""

if __name__ == "__main__":
    # Test script
    ingest_built_in_knowledge()
    print("\nTest Query: 'How to manage rice water?'")
    print("-" * 40)
    print(query_knowledge("How to manage rice water?"))
