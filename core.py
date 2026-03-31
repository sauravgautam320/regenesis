import requests
import json
import time
import os
import sys
import re

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ==========================================
# 1. THE 30-NODE MVP MASTER LIST
# ==========================================
# We define the topics here. The script will automatically generate the 
# valid node_ids (e.g., "bow_drill") for the AI to use.
MASTER_TOPICS = [
    "Foraging", "Knapping", "Cordage", "Woodworking", "Fire making",
    "Shelter building", "Water filter", "Water boiling", "Bow drill", 
    "Stone axe", "Spear making", "Basketry", "Clay gathering", 
    "Pottery", "Charcoal making", "Wattle and daub", "Hide tanning", 
    "Bone tools", "Trapping", "Bow and arrow", "Fishing", 
    "Campfire cooking", "Meat smoking", "Animal tracking", 
    "Herbal medicine", "Adobe brick", "Stone masonry", 
    "Copper smelting", "Agriculture basics", "Composting",
     # --- WATER & FIRE MASTER ---
    "Solar still",          # Extracting water from dirt/sun
    "Char cloth",           # Catching sparks for fire
    "Tinder fungus",        # Carrying fire long distances (Amadou)
    "Fire piston",          # Igniting tinder using air compression
    "Hand drill",           # Friction fire (no bow needed)
    "Dakota fire hole",     # Stealth/windproof underground fire
    
    # --- WILDERNESS SHELTER ---
    "Debris hut",           # Body-heat insulated natural shelter
    "Lean-to",              # Quick wind-break shelter
    "Quinzhee",             # Snow shelter (for cold biome)
    "Earth lodge",          # Semi-subterranean long-term shelter
    "Lashing (ropework)",   # Tying logs together for structures
    
    # --- PRIMITIVE HUNTING & GATHERING ---
    "Deadfall trap",        # Crushing trap (Figure-four)
    "Snare trap",           # Catching small game
    "Fish weir",            # Primitive rock/wood fish trap in rivers
    "Atlatl",               # Spear thrower (massive hunting upgrade)
    "Sling (weapon)",       # Throwing rocks with lethal force
    "Bolas",                # Throwing weapon to entangle legs
    "Pemmican",             # Ultimate survival superfood (meat/fat)
    "Trotline",             # Passive fishing with multiple hooks

    # --- BUSHCRAFT CRAFTING & GEAR ---
    "Pitch (resin)",        # Making pine pitch glue (primitive epoxy)
    "Sinew",                # Making primitive thread from animal tendons
    "Bone awl",             # Primitive needle for sewing leather
    "Dugout canoe",         # Burning/scraping a log to make a boat
    "Snowshoe",             # Moving in deep winter
    "Birch bark container", # Crafting waterproof pots
    "Soap from ashes",      # Making lye/soap from campfires

    # --- OFF-GRID SETTLEMENT (Tier 2) ---
    "Root cellar",          # Underground refrigeration
    "Coppicing",            # Harvesting wood without killing the tree
    "Raised-bed gardening", # Early agriculture technique
    "Adobe",                # Mud-brick making
    "Cob (material)"        # Building walls with mud and straw

     # --- ADVANCED FIRE & LIGHT ---
    "Swedish torch",             # Long-lasting, self-feeding camp cooking fire
    "Earth oven",                # Cooking large game underground with hot rocks
    "Torch",                     # Portable fire/light using pitch and wood
    "Oil lamp",                  # Animal fat/oil burned in a clay bowl/seashell
    
    # --- PRIMITIVE TOOLS & WEAPONS ---
    "Hand axe",                  # The ultimate paleolithic multi-tool
    "Adze",                      # Crucial tool for hollowing out dugout canoes
    "Celt (tool)",               # Polished stone axe (massive upgrade from knapped)
    "Blowgun",                   # Silent hunting tool for small game/birds
    "Boomerang",                 # Non-returning throwing stick for hunting
    "Sickle",                    # Essential tool for harvesting grains/grasses
    
    # --- FOOD PREP & PRESERVATION ---
    "Jerky",                     # Drying meat without smoke
    "Curing (food preservation)",# Using salt/ash to preserve food
    "Mushroom hunting",          # Foraging specifically for fungi
    "Spearfishing",              # Active water hunting
    "Fish trap",                 # Woven basket traps (different from fish weir)
    
    # --- PRIMITIVE TEXTILES & CRAFTING ---
    "Bast fibre",                # Harvesting inner tree bark for heavy-duty cordage
    "Spindle whorl",             # Weighted stick to spin plant fibers into yarn
    "Nålebinding",               # Primitive knotless knitting (pre-dates knitting)
    "Gourd",                     # Growing and drying gourds for canteens/bowls
    
    # --- WILDERNESS TRAVEL & NAVIGATION ---
    "Travois",                   # A-frame drag sled for moving heavy loads (wood/meat)
    "Snow goggles",              # Slotted bone/wood to prevent snow blindness
    "Celestial navigation",      # Finding North/South using the stars
    "Punt (boat)",               # Flat-bottomed boat pushed with a pole
    
    # --- EARLY SETTLEMENT & DEFENSE (Tier 2) ---
    "Rammed earth",              # Compacting dirt to make concrete-hard walls
    "Dry stone",                 # Building rock walls/structures WITHOUT mortar
    "Palisade",                  # Defensive wooden log wall around a camp
    "Pit firing",                # Baking clay pots in a hole in the ground
    "Guano",                     # Gathering bat/bird droppings (Ultimate fertilizer/saltpeter)
    
    # --- EARLY METALLURGY & CHEMISTRY (Tier 3) ---
    "Native copper",             # Finding un-oxidized copper nuggets in nature
    "Meteoric iron",             # The only iron you can forge without smelting
    "Smelting",                  # Extracting metal from rock using extreme heat
    "Crucible",                  # A clay cup that can withstand melting metal
    "Bloomery"                   # Primitive clay furnace to make iron
]

# Generate valid node IDs (lowercase with underscores)
MVP_NODES = [t.lower().replace(" ", "_").replace("-", "_") for t in MASTER_TOPICS]

REQUIRED_KEYS = [
    "node_id", "title", "category", "biomes",
    "prerequisites", "materials", "action_steps",
    "theory", "unlocks"
]

def validate_and_clean_node(node, topic="Unknown"):
    if not isinstance(node, dict): return None
        
    for key in REQUIRED_KEYS:
        if key not in node: 
            if key in ["biomes", "prerequisites", "materials", "action_steps", "unlocks"]:
                node[key] = []
            elif key == "theory":
                node[key] = ""
            else:
                return None
                
    try:
        node_id = str(topic).lower().replace(" ", "_").replace("-", "_")
        node["node_id"] = node_id
        node["category"] = str(node.get("category", "survival")).lower()
        
        if isinstance(node["action_steps"], list):
            node["action_steps"] = [list(s.values())[0] if isinstance(s, dict) else str(s) for s in node["action_steps"]]
            
        # Enforce Closed-Loop Graph! AI can ONLY link to our 30 Master Nodes.
        valid_prereqs = []
        for p in node.get("prerequisites", []):
            clean_p = str(p).lower().replace(" ", "_").replace("-", "_")
            if clean_p in MVP_NODES and clean_p != node_id:
                valid_prereqs.append(clean_p)
        node["prerequisites"] = valid_prereqs

        valid_unlocks = []
        for u in node.get("unlocks", []):
            clean_u = str(u).lower().replace(" ", "_").replace("-", "_")
            if clean_u in MVP_NODES and clean_u != node_id:
                valid_unlocks.append(clean_u)
        node["unlocks"] = valid_unlocks
        
        return node
    except Exception:
        return None

# ==========================================
# 2. PRIORITY FETCHING (Using OpenSearch)
# ==========================================
def fetch_incremental_vault(topic_list, vault_file="survival_vault.json"):
    vault = {}
    if os.path.exists(vault_file):
        with open(vault_file, "r") as f: vault = json.load(f)
    
    headers = {"User-Agent": "ReGenesisBot/1.0"}
    
    for topic in topic_list:
        if topic in vault and len(vault[topic]) > 50:
            continue
            
        success = False
        print(f"🌿 Searching Rewilding Wiki: {topic}...")
        
        # 1. USE OPENSEARCH TO FIND THE EXACT TITLE (Fixes the Bow-drill hyphen issue)
        search_url = "https://rewild.fandom.com/api.php"
        search_params = {"action": "opensearch", "search": topic, "limit": 1, "format": "json"}
        
        try:
            search_resp = requests.get(search_url, params=search_params, headers=headers).json()
            if len(search_resp) > 1 and len(search_resp[1]) > 0:
                exact_title = search_resp[1][0] # Grabs "Bow-drill" instead of "Bow drill"
                
                # Now fetch the text using the exact title
                query_params = {
                    "action": "query", "format": "json", 
                    "titles": exact_title, "prop": "extracts", 
                    "explaintext": "1", "redirects": "1"
                }
                page_resp = requests.get(search_url, params=query_params, headers=headers).json()
                pages = page_resp.get("query", {}).get("pages", {})
                page = next(iter(pages.values()))
                
                # Fandom extracts are sometimes empty or just redirect text. Ensure it has meat.
                if "extract" in page and len(page["extract"]) > 100:
                    clean_text = " ".join(page["extract"].split())
                    vault[topic] = clean_text[:3500]
                    print(f"  ✅ Saved {len(vault[topic])} chars from Rewilding (Exact Match: '{exact_title}').")
                    success = True
        except Exception as e:
            print(f"  ❌ Fandom API Error: {e}")

        # 2. FALLBACK TO WIKIPEDIA
        if not success:
            print(f"  🌍 Not found on Fandom. Falling back to Wikipedia: {topic}...")
            wiki_params = {
                "action": "query", "format": "json", 
                "titles": topic, "prop": "extracts", 
                "explaintext": "1", "redirects": "1"
            }
            try:
                resp = requests.get("https://en.wikipedia.org/w/api.php", params=wiki_params, headers=headers)
                pages = resp.json().get("query", {}).get("pages", {})
                page = next(iter(pages.values()))
                
                if "missing" not in page and "extract" in page and len(page["extract"]) > 0:
                    clean_text = " ".join(page["extract"].split())
                    vault[topic] = clean_text[:3500]
                    print(f"  ✅ Saved {len(vault[topic])} chars from Wikipedia.")
                    success = True
                else:
                    print(f"  ⚠️ No content found anywhere for {topic}.")
            except Exception as e:
                print(f"  ❌ Wikipedia API Error: {e}")
                
        if success:
            with open(vault_file, "w") as f: json.dump(vault, f, indent=4)
            time.sleep(1) # Be polite to APIs
            
    return vault

# ==========================================
# 3. AI STRUCTURING (Game Designer Persona)
# ==========================================
def generate_node_json(topic, wiki_text):
    print(f"🧠 AI thinking about: {topic}...")
    
    json_template = {
        "node_id": topic.lower().replace(" ", "_").replace("-", "_"),
        "title": topic,
        "category": "survival",
        "biomes": [],
        "prerequisites": [],
        "materials": ["item 1"],
        "action_steps": ["Step 1"],
        "theory": "Short explanation",
        "unlocks": []
    }
    
    prompt = f"""Task: Act as a game designer for a realistic survival tech-tree. 
Topic: {topic}

RULES:
1. Output ONLY ONE SINGLE JSON object {{}}. DO NOT output a list or array [].
2. Read the provided TEXT to accurately summarize the 'theory', 'materials', and 'action_steps'.
3. CRITICAL GRAPH LOGIC: For 'prerequisites' and 'unlocks', you MUST ONLY choose exactly from this allowed list of IDs:
   ALLOWED IDs: {MVP_NODES}
   If no IDs fit perfectly, leave the array empty []. Do NOT invent new IDs.
4. For 'biomes', choose from: ["forest", "desert", "tundra", "jungle", "urban", "universal"].
5. DO NOT wrap the output in markdown (no ```json).

TEMPLATE TO FILL OUT:
{json.dumps(json_template, indent=2)}

TEXT TO ANALYZE:
{wiki_text}"""

    model_name = os.environ.get("MODEL_NAME", "gemma3:4b")
    payload = {"model": model_name, "prompt": prompt, "stream": False, "format": "json"}
    
    try:
        resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
    except Exception: return None

    print(f"  ℹ️ AI status: {resp.status_code} (model={model_name})")
    
    try:
        res_data = resp.json()
        response_field = res_data.get("response", "")
        ai_json = None

        if isinstance(response_field, dict):
            ai_json = response_field
        elif isinstance(response_field, str):
            clean_text = re.sub(r"^```json\s*", "", response_field, flags=re.MULTILINE)
            clean_text = re.sub(r"^```\s*", "", clean_text, flags=re.MULTILINE)
            start = clean_text.find('{')
            end = clean_text.rfind('}')
            if start != -1 and end != -1:
                try: ai_json = json.loads(clean_text[start:end+1])
                except: pass

        if isinstance(ai_json, list) and len(ai_json) > 0:
            ai_json = ai_json[0]

        if not ai_json: return None
        return validate_and_clean_node(ai_json, topic)
    except Exception:
        return None

# ==========================================
# 4. EXECUTION PIPELINE
# ==========================================
if __name__ == "__main__":
    db_file = "genesis_nodes.json"
    results = []
    
    if os.path.exists(db_file):
        with open(db_file, "r") as f:
            try:
                raw_data = json.load(f)
                results = [n for n in raw_data if isinstance(n, dict) and "node_id" in n]
            except: pass

    processed_titles = {n["title"].lower() for n in results if "title" in n}
    
    # Run the fetcher on all 30 nodes!
    data_vault = fetch_incremental_vault(MASTER_TOPICS)

    for topic, text in data_vault.items():
        if topic.lower() in processed_titles: continue
            
        node = generate_node_json(topic, text)
        if node:
            results.append(node)
            processed_titles.add(node["title"].lower())
            with open(db_file, "w") as f: json.dump(results, f, indent=4)
            print(f"  💾 Success: {node['title']} added to DB.")
        else:
            print(f"  ⚠️ AI failed to structure {topic}.")

    print(f"\n🎉 Finished. Database size: {len(results)}")


