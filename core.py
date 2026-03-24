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
    "Copper smelting", "Agriculture basics", "Composting"
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
# import requests
# import json
# import time
# import os
# import sys
# import re
# # Ensure stdout uses UTF-8 so emoji prints don't raise on Windows consoles
# try:
#     sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# except Exception:
#     pass

# # ==========================================
# # 1. DATA MODELS & VALIDATION
# # ==========================================
# REQUIRED_KEYS = [
#     "node_id", "title", "category", "biomes",
#     "prerequisites", "materials", "action_steps",
#     "theory", "unlocks"
# ]

# def validate_and_clean_node(node, topic="Unknown"):
#     if not isinstance(node, dict): 
#         print(f"    ⚠️ Validation failed for {topic}: Output is not a dictionary.")
#         return None
        
#     for key in REQUIRED_KEYS:
#         if key not in node: 
#             print(f"    ⚠️ Validation failed for {topic}: Missing required key '{key}'")
#             # Auto-fix missing list keys to keep the pipeline moving
#             if key in ["biomes", "prerequisites", "materials", "action_steps", "unlocks"]:
#                 print(f"    🔧 Auto-fixing: Added empty list for '{key}'")
#                 node[key] = []
#             elif key == "theory":
#                 node[key] = ""
#             else:
#                 return None
                
#     try:
#         node["node_id"] = str(node.get("node_id", topic)).lower().replace(" ", "_")
#         node["category"] = str(node.get("category", "survival")).lower()
#         if isinstance(node["action_steps"], list):
#             node["action_steps"] = [list(s.values())[0] if isinstance(s, dict) else str(s) for s in node["action_steps"]]
#         return node
#     except Exception as e:
#         print(f"    ⚠️ Validation error during cleaning {topic}: {e}")
#         return None

# # ==========================================
# # 2. INCREMENTAL WIKIPEDIA FETCHING
# # ==========================================
# def fetch_incremental_vault(topic_list, vault_file="wikipedia_vault.json"):
#     vault = {}
#     if os.path.exists(vault_file):
#         with open(vault_file, "r") as f: vault = json.load(f)
    
#     headers = {"User-Agent": "SkillTreeBot/1.0"}
    
#     for topic in topic_list:
#         if topic in vault and len(vault[topic]) > 50:
#             continue
        
#         print(f"🌍 Scraping Wikipedia: {topic}...")
#         params = {"action": "query", "format": "json", "titles": topic, "prop": "extracts", "explaintext": True}
#         try:
#             response = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers)
#             res_json = response.json()
#             pages = res_json.get("query", {}).get("pages", {})
#             page = next(iter(pages.values()))
            
#             if "extract" in page and len(page["extract"]) > 0:
#                 # Clean text: remove multiple newlines and limit size
#                 clean_text = " ".join(page["extract"].split())
#                 vault[topic] = clean_text[:2500]
#                 print(f"  ✅ Saved {len(vault[topic])} chars for {topic}")
#                 with open(vault_file, "w") as f: json.dump(vault, f, indent=4)
#             else:
#                 print(f"  ⚠️ No content found for {topic}")
#         except Exception as e:
#             print(f"  ❌ Fetch Error for {topic}: {e}")
            
#     return vault

# # ==========================================
# # 3. AI STRUCTURING
# # ==========================================

# def generate_node_json(topic, wiki_text):
#     print(f"🧠 AI thinking about: {topic}...")
    
#     json_template = {
#         "node_id": topic.lower().replace(" ", "_"),
#         "title": topic,
#         "category": "survival",
#         "biomes": [],
#         "prerequisites": [],
#         "materials": ["item 1", "item 2"],
#         "action_steps": ["Step 1", "Step 2"],
#         "theory": "Short explanation",
#         "unlocks": []
#     }
    
#     # 1. UPDATED PROMPT: Explicitly forbid arrays/lists
#     prompt = f"""Task: Convert the text into ONE single JSON object for a survival game tech tree.
# Topic: {topic}

# RULES:
# 1. Output ONLY ONE SINGLE JSON object {{}}. DO NOT output a list or array [].
# 2. Summarize the entire text into this single node.
# 3. DO NOT wrap the output in markdown (no ```json).
# 4. You MUST include EVERY key from the template below.

# TEMPLATE TO FILL OUT:
# {json.dumps(json_template, indent=2)}

# TEXT TO ANALYZE:
# {wiki_text}"""

#     model_name = os.environ.get("MODEL_NAME", "gemma3:4b")

#     payload = {
#         "model": model_name, 
#         "prompt": prompt, 
#         "stream": False,
#         "format": "json" 
#     }
    
#     try:
#         resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
#     except Exception as e:
#         print(f"  ❌ AI request error for {topic}: {e}")
#         return None

#     print(f"  ℹ️ AI status: {resp.status_code} (model={model_name})")
#     resp_text = resp.text or ""
#     safe_name = str(topic).lower().replace(" ", "_")

#     try:
#         debug_dir = "ai_debug"
#         os.makedirs(debug_dir, exist_ok=True)
#         with open(os.path.join(debug_dir, f"{safe_name}.resp.txt"), "w", encoding="utf-8") as df:
#             df.write(resp_text)
#     except Exception: pass

#     try:
#         res_data = resp.json()
#     except Exception:
#         print(f"  ⚠️ AI response not JSON for {topic}")
#         return None

#     if resp.status_code != 200:
#         print(f"  ❌ AI server error: {resp_text}")
#         return None

#     response_field = res_data.get("response", "")
#     ai_json = None

#     if isinstance(response_field, dict):
#         ai_json = response_field
#     elif isinstance(response_field, str):
#         clean_text = re.sub(r"^```json\s*", "", response_field, flags=re.MULTILINE)
#         clean_text = re.sub(r"^```\s*", "", clean_text, flags=re.MULTILINE)
#         clean_text = clean_text.strip()
        
#         try:
#             ai_json = json.loads(clean_text)
#         except Exception:
#             # Safer fallback: Extract from first { to last }
#             start = clean_text.find('{')
#             end = clean_text.rfind('}')
#             if start != -1 and end != -1:
#                 try:
#                     ai_json = json.loads(clean_text[start:end+1])
#                 except Exception:
#                     pass

#     # 2. THE CRITICAL FIX: If AI still returns a list, just grab the first object
#     if isinstance(ai_json, list):
#         if len(ai_json) > 0:
#             print(f"  ⚠️ AI returned a list of {len(ai_json)} items. Grabbing the main topic (first item).")
#             ai_json = ai_json[0]
#         else:
#             ai_json = None

#     if not ai_json:
#         print(f"  ⚠️ AI produced no parseable JSON for {topic}; see ai_debug/{safe_name}.resp.txt")
#         return None

#     return validate_and_clean_node(ai_json, topic)
# # ==========================================
# # 4. EXECUTION PIPELINE
# # ==========================================
# if __name__ == "__main__":
#     topics = ["Bow drill", "Water filter", "Knapping", "Wattle and daub"]
#     db_file = "genesis_nodes.json"
    
#     results = []
#     if os.path.exists(db_file):
#         with open(db_file, "r") as f:
#             try:
#                 raw_data = json.load(f)
#                 results = [n for n in raw_data if isinstance(n, dict) and "node_id" in n]
#             except: pass

#     processed_titles = {n["title"].lower() for n in results if "title" in n}
#     data_vault = fetch_incremental_vault(topics)

#     for topic, text in data_vault.items():
#         if topic.lower() in processed_titles: continue
            
#         node = generate_node_json(topic, text)
#         if node:
#             results.append(node)
#             processed_titles.add(node["title"].lower())
#             with open(db_file, "w") as f: json.dump(results, f, indent=4)
#             print(f"  💾 Success: {node['title']} added to DB.")
#         else:
#             print(f"  ⚠️ AI failed to structure {topic}.")

#     print(f"\n🎉 Finished. Database size: {len(results)}")

