"""
Support AI Agent — Python Backend
Connects to local Ollama LLM and traverses Microsoft CCaaS Knowledge Graph
to provide resolution steps for support tickets.
"""

import json
import os
import http.server
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
import mimetypes
import time
from socketserver import ThreadingMixIn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Try to import Azure OpenAI (optional)
try:
    from openai import AzureOpenAI
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("[WARNING] openai package not installed. Azure OpenAI support disabled.")
    print("          Install with: pip install openai")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KG_PATH = os.path.join(BASE_DIR, "knowledge_graph.json")  # Default graph
DATA_DIR = os.path.join(BASE_DIR, "data")

# LLM Provider Configuration
# Azure OpenAI is DISABLED - using Ollama only
USE_AZURE_OPENAI = False  # Hardcoded to False to disable Azure OpenAI

# Ollama Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"  # Change to your installed Ollama model

# Azure OpenAI Configuration (from .env)
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
AZURE_OPENAI_MODEL = os.getenv('KG_AGENT_MODEL', 'gpt-4o-mini')

# Initialize Azure OpenAI client if configured
azure_client = None
if USE_AZURE_OPENAI and AZURE_AVAILABLE and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY:
    try:
        azure_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        print(f"[INFO] Azure OpenAI client initialized: {AZURE_OPENAI_MODEL}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Azure OpenAI client: {e}")
        azure_client = None
elif USE_AZURE_OPENAI:
    print("[WARNING] USE_AZURE_OPENAI=true but credentials missing or openai not installed")


# ─── Knowledge Graph Loader ─────────────────────────────────────────────────

def load_knowledge_graph(graph_path=None):
    """Load knowledge graph from specified path or use default KG_PATH."""
    path = graph_path or KG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def reload_knowledge_graph(graph_file):
    """Reload knowledge graph from a new file."""
    global KG, NODES, EDGES, KG_PATH
    
    new_path = os.path.join(BASE_DIR, graph_file)
    if not os.path.exists(new_path):
        raise FileNotFoundError(f"Graph file not found: {graph_file}")
    
    KG = load_knowledge_graph(new_path)
    NODES = {n["id"]: n for n in KG["nodes"]}
    EDGES = KG["edges"]
    KG_PATH = new_path
    
    print(f"[INFO] Knowledge graph reloaded: {graph_file}")
    print(f"[INFO] Loaded {len(NODES)} nodes, {len(EDGES)} edges")
    return True


def list_available_graphs():
    """List all available knowledge graph JSON files."""
    import glob
    graphs = []
    
    # Find all knowledge_graph*.json files
    pattern = os.path.join(BASE_DIR, "knowledge_graph*.json")
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        # Create display name from filename
        display_name = filename.replace("knowledge_graph", "KG").replace(".json", "").replace("_", " ").title()
        if display_name == "KG":
            display_name = "Default Graph"
        
        # Get file size and modification time
        stat = os.stat(filepath)
        
        graphs.append({
            "filename": filename,
            "display_name": display_name,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
        })
    
    # Sort by filename
    graphs.sort(key=lambda x: x["filename"])
    return graphs


KG = load_knowledge_graph()
NODES = {n["id"]: n for n in KG["nodes"]}
EDGES = KG["edges"]


# ─── Graph Traversal Engine ─────────────────────────────────────────────────

def find_neighbors(node_id, direction="outgoing"):
    """Find all nodes connected to the given node_id."""
    results = []
    for e in EDGES:
        if direction == "outgoing" and e["source"] == node_id:
            target = NODES.get(e["target"])
            if target:
                results.append({"edge_type": e["type"], "node": target})
        elif direction == "incoming" and e["target"] == node_id:
            source = NODES.get(e["source"])
            if source:
                results.append({"edge_type": e["type"], "node": source})
        elif direction == "both":
            if e["source"] == node_id:
                target = NODES.get(e["target"])
                if target:
                    results.append({"edge_type": e["type"], "node": target})
            elif e["target"] == node_id:
                source = NODES.get(e["source"])
                if source:
                    results.append({"edge_type": e["type"], "node": source})
    return results


def search_nodes_by_keywords(keywords):
    """Search nodes by keywords in label, tags, and properties."""
    keywords_lower = [k.lower() for k in keywords]
    scored = []
    for nid, node in NODES.items():
        score = 0
        label_lower = node["label"].lower()
        tags_lower = [t.lower() for t in node.get("tags", [])]
        props_str = json.dumps(node.get("properties", {})).lower()

        for kw in keywords_lower:
            if kw in label_lower:
                score += 10
            for tag in tags_lower:
                if kw in tag:
                    score += 5
            if kw in props_str:
                score += 2
        if score > 0:
            scored.append((score, node))

    scored.sort(key=lambda x: -x[0])
    return [item[1] for item in scored[:10]]


def extract_keywords(ticket_text):
    """Extract relevant keywords from ticket text."""
    # Common CCaaS-related keywords to look for
    keyword_map = {
        "voice": ["voice", "call", "phone", "inbound", "outbound", "ivr", "dial"],
        "routing": ["routing", "route", "queue", "assignment", "workstream", "skill"],
        "chat": ["chat", "messaging", "whatsapp", "sms", "widget", "digital"],
        "copilot": ["copilot", "ai", "suggestion", "summarization", "draft"],
        "transfer": ["transfer", "warm transfer", "cold transfer", "consult"],
        "agent": ["agent", "desktop", "workspace", "presence", "login", "session"],
        "analytics": ["analytics", "dashboard", "report", "metrics", "supervisor"],
        "bot": ["bot", "virtual agent", "self-service", "copilot studio", "pva"],
        "safari": ["safari", "browser", "widget", "cookie", "itp"],
        "latency": ["slow", "delay", "latency", "timeout", "spinning"],
        "outage": ["outage", "down", "unavailable", "error", "failure", "drop", "crash", "crashed", "hang", "freeze", "system"],
        "recording": ["recording", "transcription", "transcript"],
        "knowledge": ["knowledge", "article", "kb", "documentation"],
        "configuration": ["config", "configuration", "setting", "setup", "admin"],
        "escalation": ["escalation", "escalate", "p1", "critical", "urgent", "sev1"],
        "customer": ["contoso", "fabrikam", "northwind"],
    }

    text_lower = ticket_text.lower()
    found_keywords = set()

    for category, terms in keyword_map.items():
        for term in terms:
            if term in text_lower:
                found_keywords.add(category)
                found_keywords.add(term)

    # Also extract individual words as fallback
    words = text_lower.split()
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                  "to", "for", "of", "with", "and", "or", "not", "from", "by",
                  "it", "this", "that", "be", "has", "have", "had", "do", "does",
                  "did", "will", "would", "can", "could", "should", "may", "might",
                  "i", "we", "they", "he", "she", "our", "their", "my", "your",
                  "but", "if", "when", "then", "than", "no", "yes", "all", "any",
                  "some", "been", "being", "about", "into", "through", "after",
                  "before", "between", "out", "up", "down", "just", "also", "very",
                  "so", "too", "here", "there", "how", "what", "which", "who"}

    for word in words:
        cleaned = word.strip(".,!?;:\"'()[]{}").lower()
        if len(cleaned) > 2 and cleaned not in stop_words:
            found_keywords.add(cleaned)

    return list(found_keywords)


def read_document(doc_path):
    """Read a document file from the data folder."""
    full_path = os.path.join(BASE_DIR, doc_path)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def traverse_graph_for_ticket(ticket_text):
    """
    Main graph traversal logic for a support ticket.
    Returns structured context from the knowledge graph.
    """
    keywords = extract_keywords(ticket_text)
    matched_nodes = search_nodes_by_keywords(keywords)

    context = {
        "matched_services": [],
        "known_issues": [],
        "runbooks": [],
        "sops": [],
        "faqs": [],
        "experts": [],
        "user_guides": [],
        "release_notes": [],
        "past_incidents": [],
        "documents": [],
        "customers": [],
    }

    visited = set()

    def collect_node(node):
        nid = node["id"]
        if nid in visited:
            return
        visited.add(nid)

        ntype = node["type"]
        if ntype == "Service":
            context["matched_services"].append(node)
        elif ntype == "KnownIssue":
            context["known_issues"].append(node)
        elif ntype == "Runbook":
            context["runbooks"].append(node)
        elif ntype == "SOP":
            context["sops"].append(node)
        elif ntype == "FAQ":
            context["faqs"].append(node)
        elif ntype == "Expert":
            context["experts"].append(node)
        elif ntype == "UserGuide":
            context["user_guides"].append(node)
        elif ntype == "ReleaseNote":
            context["release_notes"].append(node)
        elif ntype == "Incident":
            context["past_incidents"].append(node)
        elif ntype == "Customer":
            context["customers"].append(node)

        # Read associated document if present
        doc_path = node.get("properties", {}).get("document")
        if doc_path:
            doc_content = read_document(doc_path)
            if doc_content:
                context["documents"].append({
                    "source": node["label"],
                    "type": ntype,
                    "path": doc_path,
                    "content": doc_content[:1000]  # Trimmed for faster LLM
                })

    # Process matched nodes and their neighbors
    for node in matched_nodes:
        collect_node(node)
        neighbors = find_neighbors(node["id"], direction="both")
        for neighbor in neighbors:
            collect_node(neighbor["node"])

    return context, keywords


def build_llm_prompt(ticket_text, context, keywords):
    """Build structured prompt for the LLM."""
    prompt_parts = []
    prompt_parts.append("You are a Support AI Agent for Microsoft Dynamics 365 Contact Center (CCaaS).")
    prompt_parts.append("Your role is to help support engineers resolve tickets quickly by providing ")
    prompt_parts.append("step-by-step solutions based on the knowledge graph data below.\n")
    prompt_parts.append("=" * 60)
    prompt_parts.append(f"\nSUPPORT TICKET:\n{ticket_text}\n")
    prompt_parts.append("=" * 60)
    prompt_parts.append(f"\nKEYWORDS IDENTIFIED: {', '.join(keywords[:15])}\n")

    # Known Issues
    if context["known_issues"]:
        prompt_parts.append("\n--- KNOWN ISSUES (check these first!) ---")
        for ki in context["known_issues"]:
            p = ki.get("properties", {})
            prompt_parts.append(f"\n[{ki['id']}] {ki['label']}")
            prompt_parts.append(f"  Severity: {p.get('severity', 'N/A')}")
            prompt_parts.append(f"  Status: {p.get('status', 'N/A')}")
            prompt_parts.append(f"  Symptoms: {json.dumps(p.get('symptoms', []))}")
            prompt_parts.append(f"  Root Cause: {p.get('root_cause', 'N/A')}")
            prompt_parts.append(f"  Workaround: {p.get('workaround', 'N/A')}")

    # Runbooks
    if context["runbooks"]:
        prompt_parts.append("\n\n--- RUNBOOKS (step-by-step recovery) ---")
        for rb in context["runbooks"]:
            p = rb.get("properties", {})
            prompt_parts.append(f"\n[{rb['id']}] {rb['label']}")
            prompt_parts.append(f"  Estimated Time: {p.get('estimated_time', 'N/A')}")
            for step in p.get("steps", []):
                prompt_parts.append(f"  {step}")

    # FAQs
    if context["faqs"]:
        prompt_parts.append("\n\n--- FREQUENTLY ASKED QUESTIONS ---")
        for faq in context["faqs"]:
            p = faq.get("properties", {})
            prompt_parts.append(f"\nQ: {p.get('question', 'N/A')}")
            prompt_parts.append(f"A: {p.get('answer', 'N/A')}")

    # SOPs
    if context["sops"]:
        prompt_parts.append("\n\n--- STANDARD OPERATING PROCEDURES ---")
        for sop in context["sops"]:
            p = sop.get("properties", {})
            prompt_parts.append(f"\n[{sop['id']}] {sop['label']}")
            for step in p.get("steps", []):
                prompt_parts.append(f"  {step}")

    # Past Incidents
    if context["past_incidents"]:
        prompt_parts.append("\n\n--- PAST INCIDENTS (similar issues) ---")
        for inc in context["past_incidents"]:
            p = inc.get("properties", {})
            prompt_parts.append(f"\n[{inc['id']}] {inc['label']}")
            prompt_parts.append(f"  Date: {p.get('date', 'N/A')}")
            prompt_parts.append(f"  Root Cause: {p.get('root_cause', 'N/A')}")
            prompt_parts.append(f"  Resolution: {p.get('resolution', 'N/A')}")

    # Experts
    if context["experts"]:
        prompt_parts.append("\n\n--- SUBJECT MATTER EXPERTS ---")
        for exp in context["experts"]:
            p = exp.get("properties", {})
            prompt_parts.append(f"\n{exp['label']} — {p.get('role', 'N/A')}")
            prompt_parts.append(f"  Expertise: {', '.join(p.get('expertise', []))}")
            prompt_parts.append(f"  Email: {p.get('email', 'N/A')}")
            prompt_parts.append(f"  On-Call: {p.get('on_call', 'N/A')}")

    # Matched Services
    if context["matched_services"]:
        prompt_parts.append("\n\n--- AFFECTED SERVICES ---")
        for svc in context["matched_services"]:
            p = svc.get("properties", {})
            prompt_parts.append(f"\n{svc['label']} ({p.get('service_id', 'N/A')})")
            prompt_parts.append(f"  Description: {p.get('description', 'N/A')}")
            prompt_parts.append(f"  Criticality: {p.get('criticality', 'N/A')}")

    # Documents (limited to 2 docs, 500 chars each for speed)
    if context["documents"]:
        prompt_parts.append("\n\n--- RELEVANT DOCUMENTS ---")
        for doc in context["documents"][:2]:  # Limit to 2 docs
            prompt_parts.append(f"\n[{doc['type']}] {doc['source']}:")
            prompt_parts.append(doc["content"][:500])

    prompt_parts.append("\n\n" + "=" * 60)
    prompt_parts.append("\nBased on the knowledge graph data above, provide:")
    prompt_parts.append("1. **Root Cause Analysis**: What is likely causing this issue?")
    prompt_parts.append("2. **Immediate Steps**: Step-by-step actions to resolve or mitigate now")
    prompt_parts.append("3. **Known Issue Match**: Does this match any known issue? If yes, provide workaround")
    prompt_parts.append("4. **Escalation**: If P1, outline the escalation path")
    prompt_parts.append("5. **Expert Contact**: Who should be contacted for this issue?")
    prompt_parts.append("\nBe concise, actionable, and reference specific document IDs where relevant.")

    return "\n".join(prompt_parts)


# ─── LLM Integration ────────────────────────────────────────────────────────

def query_azure_openai(prompt):
    """Send prompt to Azure OpenAI and get response."""
    if not azure_client:
        return "Error: Azure OpenAI client not initialized. Check your .env configuration."
    
    try:
        print(f"[DEBUG]    Azure OpenAI request sent (model: {AZURE_OPENAI_MODEL})")
        t_start = time.time()
        
        response = azure_client.chat.completions.create(
            model=AZURE_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful support assistant for Microsoft Dynamics 365 Contact Center (CCaaS). Provide clear, actionable solutions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1024,
            top_p=0.9
        )
        
        t_end = time.time()
        response_text = response.choices[0].message.content
        print(f"[DEBUG]    Azure OpenAI response received: {t_end-t_start:.3f}s ({len(response_text)} chars)")
        return response_text
        
    except Exception as e:
        print(f"[DEBUG]    Azure OpenAI ERROR: {e}")
        return f"Error calling Azure OpenAI: {e}"


def query_ollama(prompt):
    """Send prompt to local Ollama and get full response (non-streaming fallback)."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 1024
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        print(f"[DEBUG]    Ollama request sent to {OLLAMA_URL}")
        t_ollama_start = time.time()
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
            t_ollama_end = time.time()
            print(f"[DEBUG]    Ollama raw response received: {t_ollama_end-t_ollama_start:.3f}s ({len(raw)} bytes)")
            result = json.loads(raw)
            return result.get("response", "No response from LLM.")
    except urllib.error.URLError as e:
        print(f"[DEBUG]    Ollama ERROR: {e}")
        return f"Error connecting to Ollama: {e}. Make sure Ollama is running (ollama serve) and model '{OLLAMA_MODEL}' is pulled."
    except Exception as e:
        print(f"[DEBUG]    Ollama EXCEPTION: {e}")
        return f"Error: {str(e)}"


def query_llm(prompt):
    """Unified LLM query function - routes to Azure OpenAI or Ollama based on configuration."""
    if USE_AZURE_OPENAI and azure_client:
        return query_azure_openai(prompt)
    else:
        return query_ollama(prompt)


def stream_azure_openai(prompt):
    """Stream response from Azure OpenAI using SSE, yields (chunk_text, is_done) tuples."""
    if not azure_client:
        yield ("Error: Azure OpenAI client not initialized.", True)
        return
    
    try:
        print(f"[DEBUG]    Azure OpenAI STREAMING request sent (model: {AZURE_OPENAI_MODEL})")
        t_start = time.time()
        first_token = True
        
        stream = azure_client.chat.completions.create(
            model=AZURE_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful support assistant for Microsoft Dynamics 365 Contact Center (CCaaS). Provide clear, actionable solutions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1024,
            top_p=0.9,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    if first_token:
                        print(f"[DEBUG]    Time to first token: {time.time()-t_start:.3f}s")
                        first_token = False
                    yield (delta.content, False)
            
            # Check if done
            if chunk.choices and chunk.choices[0].finish_reason:
                yield ("", True)
                break
        
        print(f"[DEBUG]    Azure OpenAI stream total: {time.time()-t_start:.3f}s")
        
    except Exception as e:
        print(f"[DEBUG]    Azure OpenAI STREAMING ERROR: {e}")
        yield (f"Error streaming from Azure OpenAI: {e}", True)


def stream_ollama(prompt):
    """Send prompt to Ollama with stream=True, yields (chunk_text, is_done) tuples."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 1024
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        print(f"[DEBUG]    Ollama STREAMING request sent to {OLLAMA_URL}")
        t_start = time.time()
        resp = urllib.request.urlopen(req, timeout=300)
        first_token = True
        buf = b""
        while True:
            chunk = resp.read(1)
            if not chunk:
                break
            buf += chunk
            if chunk == b"\n":
                line = buf.decode("utf-8").strip()
                buf = b""
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if first_token:
                    print(f"[DEBUG]    Time to first token: {time.time()-t_start:.3f}s")
                    first_token = False
                token = obj.get("response", "")
                done = obj.get("done", False)
                yield token, done
                if done:
                    print(f"[DEBUG]    Ollama stream total: {time.time()-t_start:.3f}s")
                    break
        resp.close()
    except urllib.error.URLError as e:
        print(f"[DEBUG]    Ollama STREAM ERROR: {e}")
        yield f"Error connecting to Ollama: {e}", True
    except Exception as e:
        print(f"[DEBUG]    Ollama STREAM EXCEPTION: {e}")
        yield f"Error: {str(e)}", True


def stream_llm(prompt):
    """Unified LLM streaming function - routes to Azure OpenAI or Ollama based on configuration."""
    if USE_AZURE_OPENAI and azure_client:
        yield from stream_azure_openai(prompt)
    else:
        yield from stream_ollama(prompt)


def generate_fallback_response(ticket_text, context, keywords):
    """Generate a structured response without LLM (fallback if Ollama is unavailable)."""
    parts = []
    parts.append("## Support AI Agent — Knowledge Graph Analysis\n")
    parts.append(f"**Keywords Detected:** {', '.join(keywords[:10])}\n")

    if context["known_issues"]:
        parts.append("### 🔴 Known Issues Match\n")
        for ki in context["known_issues"]:
            p = ki.get("properties", {})
            parts.append(f"**{ki['label']}** (Severity: {p.get('severity', 'N/A')})\n")
            parts.append(f"- Status: {p.get('status', 'N/A')}\n")
            symptoms = p.get("symptoms", [])
            if symptoms:
                parts.append("- Symptoms:\n")
                for s in symptoms:
                    parts.append(f"  - {s}\n")
            parts.append(f"- Root Cause: {p.get('root_cause', 'N/A')}\n")
            parts.append(f"- Workaround: {p.get('workaround', 'N/A')}\n\n")

    if context["runbooks"]:
        parts.append("### 📋 Applicable Runbooks\n")
        for rb in context["runbooks"]:
            p = rb.get("properties", {})
            parts.append(f"**{rb['label']}** (Est. Time: {p.get('estimated_time', 'N/A')})\n")
            for step in p.get("steps", []):
                parts.append(f"{step}\n")
            parts.append("\n")

    if context["faqs"]:
        parts.append("### ❓ Related FAQs\n")
        for faq in context["faqs"]:
            p = faq.get("properties", {})
            parts.append(f"**Q:** {p.get('question', 'N/A')}\n")
            parts.append(f"**A:** {p.get('answer', 'N/A')}\n\n")

    if context["sops"]:
        parts.append("### 📝 SOPs to Follow\n")
        for sop in context["sops"]:
            p = sop.get("properties", {})
            parts.append(f"**{sop['label']}**\n")
            for step in p.get("steps", []):
                parts.append(f"{step}\n")
            parts.append("\n")

    if context["past_incidents"]:
        parts.append("### 📊 Similar Past Incidents\n")
        for inc in context["past_incidents"]:
            p = inc.get("properties", {})
            parts.append(f"**{inc['label']}** ({p.get('date', 'N/A')})\n")
            parts.append(f"- Root Cause: {p.get('root_cause', 'N/A')}\n")
            parts.append(f"- Resolution: {p.get('resolution', 'N/A')}\n\n")

    if context["experts"]:
        parts.append("### 👤 Contact These Experts\n")
        for exp in context["experts"]:
            p = exp.get("properties", {})
            on_call = "✅ On-Call" if p.get("on_call") else "❌ Not On-Call"
            parts.append(f"**{exp['label']}** — {p.get('role', 'N/A')} ({on_call})\n")
            parts.append(f"- Expertise: {', '.join(p.get('expertise', []))}\n")
            parts.append(f"- Email: {p.get('email', 'N/A')}\n\n")

    if context["matched_services"]:
        parts.append("### 🔧 Affected Services\n")
        for svc in context["matched_services"]:
            p = svc.get("properties", {})
            parts.append(f"**{svc['label']}** — Criticality: {p.get('criticality', 'N/A')}\n")
            parts.append(f"- {p.get('description', 'N/A')}\n\n")

    if context["documents"]:
        parts.append("### 📄 Referenced Documents\n")
        for doc in context["documents"]:
            parts.append(f"- [{doc['type']}] {doc['source']} → `{doc['path']}`\n")

    if not any([context["known_issues"], context["runbooks"], context["faqs"],
                context["experts"], context["matched_services"]]):
        parts.append("No specific matches found in the knowledge graph. ")
        parts.append("Please provide more details about the issue or try different keywords.\n")
        parts.append(f"\nSearch attempted with keywords: {', '.join(keywords)}")

    return "".join(parts)


# ─── HTTP Server ─────────────────────────────────────────────────────────────

class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """HTTP Server that handles each request in a separate thread"""
    daemon_threads = True  # Don't wait for threads when shutting down
    allow_reuse_address = True


class SupportAgentHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/chat":
            self._handle_chat()
        elif parsed.path == "/api/chat-stream":
            self._handle_chat_stream()
        elif parsed.path == "/api/graph-search":
            self._handle_graph_search()
        elif parsed.path == "/api/switch-graph":
            self._handle_switch_graph()
        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            llm_provider = "azure" if (USE_AZURE_OPENAI and azure_client) else "ollama"
            llm_model = AZURE_OPENAI_MODEL if (USE_AZURE_OPENAI and azure_client) else OLLAMA_MODEL
            self._send_json({
                "status": "ok",
                "llm_provider": llm_provider,
                "model": llm_model
            })
        elif parsed.path == "/api/graph-stats":
            self._send_json({
                "total_nodes": len(NODES),
                "total_edges": len(EDGES),
                "node_types": list(set(n["type"] for n in NODES.values())),
                "product": KG["metadata"]["product"],
                "current_graph": os.path.basename(KG_PATH)
            })
        elif parsed.path == "/api/list-graphs":
            # Return list of available knowledge graph files
            self._send_json({
                "graphs": list_available_graphs(),
                "current": os.path.basename(KG_PATH)
            })
        elif parsed.path == "/api/ollama-status" or parsed.path == "/api/llm-status":
            self._check_llm_status()
        elif parsed.path == "/api/document":
            self._handle_document_request(parsed)
        else:
            super().do_GET()

    def _handle_chat(self):
        t_start = time.time()
        print(f"\n{'='*60}")
        print(f"[DEBUG] ===== NEW CHAT REQUEST at {time.strftime('%H:%M:%S')} =====")

        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body.decode("utf-8"))

        ticket_text = data.get("message", "")
        use_llm = data.get("use_llm", True)
        print(f"[DEBUG] Message length: {len(ticket_text)} chars | use_llm: {use_llm}")

        if not ticket_text.strip():
            self._send_json({"error": "Empty message"}, status=400)
            return

        # Traverse knowledge graph
        t1 = time.time()
        context, keywords = traverse_graph_for_ticket(ticket_text)
        t2 = time.time()
        print(f"[DEBUG] 1. Graph traversal:    {t2-t1:.3f}s")
        print(f"[DEBUG]    Keywords: {keywords[:10]}")
        print(f"[DEBUG]    Matched: {len(context['matched_services'])} services, "
              f"{len(context['known_issues'])} known issues, "
              f"{len(context['runbooks'])} runbooks, "
              f"{len(context['experts'])} experts, "
              f"{len(context['documents'])} docs")

        # Build graph context summary
        graph_summary = {
            "keywords": keywords[:15],
            "matched_services": [n["label"] for n in context["matched_services"]],
            "known_issues": [n["label"] for n in context["known_issues"]],
            "runbooks": [{
                "label": n["label"],
                "path": n.get("properties", {}).get("document"),
                "estimated_time": n.get("properties", {}).get("estimated_time"),
                "steps": n.get("properties", {}).get("steps", [])
            } for n in context["runbooks"]],
            "faqs": [n["label"] for n in context["faqs"]],
            "experts": [n["label"] for n in context["experts"]],
            "past_incidents": [n["label"] for n in context["past_incidents"]],
            "documents": [{
                "source": d["source"],
                "type": d["type"],
                "path": d["path"],
                "content_preview": d["content"][:300] + "..." if len(d["content"]) > 300 else d["content"]
            } for d in context["documents"]],
        }
        t3 = time.time()
        print(f"[DEBUG] 2. Build summary:      {t3-t2:.3f}s")

        if use_llm:
            # Build prompt and query LLM (Azure OpenAI or Ollama)
            t4 = time.time()
            prompt = build_llm_prompt(ticket_text, context, keywords)
            t5 = time.time()
            print(f"[DEBUG] 3. Build LLM prompt:   {t5-t4:.3f}s  (prompt length: {len(prompt)} chars)")

            llm_provider = "Azure OpenAI" if (USE_AZURE_OPENAI and azure_client) else "Ollama"
            llm_model = AZURE_OPENAI_MODEL if (USE_AZURE_OPENAI and azure_client) else OLLAMA_MODEL
            print(f"[DEBUG] 4. Calling {llm_provider} ({llm_model})...")
            t6 = time.time()
            response_text = query_llm(prompt)
            t7 = time.time()
            print(f"[DEBUG] 4. {llm_provider} response: {t7-t6:.3f}s  <<<< (response length: {len(response_text)} chars)")
        else:
            # Fallback: structured response from graph only
            t4 = time.time()
            response_text = generate_fallback_response(ticket_text, context, keywords)
            t5 = time.time()
            print(f"[DEBUG] 3. Fallback response:  {t5-t4:.3f}s")

        t_end = time.time()
        print(f"[DEBUG] ===== TOTAL TIME: {t_end-t_start:.3f}s =====")
        print(f"{'='*60}\n")

        self._send_json({
            "response": response_text,
            "graph_context": graph_summary,
            "mode": "llm" if use_llm else "graph-only"
        })

    def _handle_chat_stream(self):
        """SSE streaming endpoint — sends tokens as they arrive from Ollama."""
        t_start = time.time()
        print(f"\n{'='*60}")
        print(f"[DEBUG] ===== STREAMING CHAT REQUEST at {time.strftime('%H:%M:%S')} =====")

        try:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            ticket_text = data.get("message", "")
            use_llm = data.get("use_llm", True)

            if not ticket_text.strip():
                self.send_response(400)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

            # Graph traversal
            t1 = time.time()
            context, keywords = traverse_graph_for_ticket(ticket_text)
            t2 = time.time()
            print(f"[DEBUG] 1. Graph traversal:    {t2-t1:.3f}s")

            graph_summary = {
                "keywords": keywords[:15],
                "matched_services": [n["label"] for n in context["matched_services"]],
                "known_issues": [n["label"] for n in context["known_issues"]],
                "runbooks": [{
                    "label": n["label"],
                    "path": n.get("properties", {}).get("document"),
                    "estimated_time": n.get("properties", {}).get("estimated_time"),
                    "steps": n.get("properties", {}).get("steps", [])
                } for n in context["runbooks"]],
                "faqs": [n["label"] for n in context["faqs"]],
                "experts": [n["label"] for n in context["experts"]],
                "past_incidents": [n["label"] for n in context["past_incidents"]],
                "documents": [{
                    "source": d["source"],
                    "type": d["type"],
                    "path": d["path"],
                    "content_preview": d["content"][:300] + "..." if len(d["content"]) > 300 else d["content"]
                } for d in context["documents"]],
            }

            # Send SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")  # Close connection after response
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Send graph context first as a special event
            ctx_event = json.dumps({"type": "context", "graph_context": graph_summary})
            try:
                self.wfile.write(f"data: {ctx_event}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                print(f"[INFO] Client disconnected during context send")
                return

            if use_llm:
                prompt = build_llm_prompt(ticket_text, context, keywords)
                llm_provider = "Azure OpenAI" if (USE_AZURE_OPENAI and azure_client) else "Ollama"
                llm_model = AZURE_OPENAI_MODEL if (USE_AZURE_OPENAI and azure_client) else OLLAMA_MODEL
                print(f"[DEBUG] Prompt length: {len(prompt)} chars. Streaming from {llm_provider} ({llm_model})...")
                try:
                    for token, done in stream_llm(prompt):
                        if token:
                            chunk = json.dumps({"type": "token", "text": token})
                            try:
                                self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                                self.wfile.flush()
                            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                                print(f"[INFO] Client disconnected during streaming")
                                return
                        if done:
                            break
                except Exception as llm_err:
                    print(f"[ERROR] LLM streaming error: {llm_err}")
                    error_msg = f"Error during LLM processing: {str(llm_err)}"
                    chunk = json.dumps({"type": "token", "text": f"\n\n**Error:** {error_msg}"})
                    try:
                        self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        print(f"[INFO] Client disconnected during error send")
                        return
            else:
                try:
                    response_text = generate_fallback_response(ticket_text, context, keywords)
                    chunk = json.dumps({"type": "token", "text": response_text})
                    try:
                        self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        print(f"[INFO] Client disconnected during fallback send")
                        return
                except Exception as fallback_err:
                    print(f"[ERROR] Fallback response error: {fallback_err}")
                    error_msg = f"Error generating response: {str(fallback_err)}"
                    chunk = json.dumps({"type": "token", "text": f"**Error:** {error_msg}"})
                    try:
                        self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        print(f"[INFO] Client disconnected during error send")
                        return

            # Send done event
            done_event = json.dumps({"type": "done", "mode": "llm" if use_llm else "graph-only"})
            try:
                self.wfile.write(f"data: {done_event}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                print(f"[INFO] Client disconnected before done event")
                return

            t_end = time.time()
            print(f"[DEBUG] ===== STREAM TOTAL TIME: {t_end-t_start:.3f}s =====")
            print(f"{'='*60}\n")

        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_err:
            # Client disconnected - this is normal (e.g., browser closed)
            print(f"[INFO] Client disconnected: {type(conn_err).__name__}")
        except Exception as e:
            print(f"[ERROR] Chat stream handler error: {e}")
            import traceback
            traceback.print_exc()
            try:
                # Try to send error event if headers haven't been sent yet
                if not hasattr(self, '_headers_sent'):
                    self.send_response(500)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                # Send error as SSE event
                error_event = json.dumps({"type": "error", "message": str(e)})
                self.wfile.write(f"data: {error_event}\n\n".encode("utf-8"))
                done_event = json.dumps({"type": "done", "mode": "error"})
                self.wfile.write(f"data: {done_event}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Client already disconnected, can't send error
                pass
            except:
                pass  # If we can't send error, connection is already broken

    def _handle_graph_search(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        data = json.loads(body.decode("utf-8"))

        query = data.get("query", "")
        keywords = extract_keywords(query)
        results = search_nodes_by_keywords(keywords)

        self._send_json({
            "keywords": keywords,
            "results": [{"id": n["id"], "type": n["type"], "label": n["label"],
                         "tags": n.get("tags", [])} for n in results]
        })

    def _handle_switch_graph(self):
        """Handle switching to a different knowledge graph file."""
        try:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            graph_file = data.get("graph_file", "")
            if not graph_file:
                self._send_json({"error": "graph_file parameter required"}, status=400)
                return

            # Reload the knowledge graph
            reload_knowledge_graph(graph_file)

            self._send_json({
                "status": "success",
                "message": f"Switched to {graph_file}",
                "graph_file": graph_file,
                "total_nodes": len(NODES),
                "total_edges": len(EDGES)
            })
        except FileNotFoundError as e:
            self._send_json({"error": str(e)}, status=404)
        except Exception as e:
            self._send_json({"error": f"Failed to switch graph: {str(e)}"}, status=500)

    def _check_llm_status(self):
        """Check status of configured LLM provider (Azure OpenAI or Ollama)."""
        response = {
            "provider": "azure" if (USE_AZURE_OPENAI and azure_client) else "ollama",
            "use_azure": USE_AZURE_OPENAI
        }
        
        if USE_AZURE_OPENAI and azure_client:
            # Azure OpenAI status
            try:
                # Quick test to verify connectivity
                test_response = azure_client.chat.completions.create(
                    model=AZURE_OPENAI_MODEL,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                response.update({
                    "status": "connected",
                    "model": AZURE_OPENAI_MODEL,
                    "endpoint": AZURE_OPENAI_ENDPOINT,
                    "api_version": AZURE_OPENAI_API_VERSION
                })
            except Exception as e:
                response.update({
                    "status": "error",
                    "error": str(e),
                    "model": AZURE_OPENAI_MODEL
                })
        else:
            # Ollama status
            try:
                req = urllib.request.Request("http://localhost:11434/api/tags")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", [])]
                    response.update({
                        "status": "connected",
                        "models": models,
                        "selected_model": OLLAMA_MODEL,
                        "model_available": any(OLLAMA_MODEL in m for m in models)
                    })
            except Exception:
                response.update({
                    "status": "disconnected",
                    "error": "Cannot connect to Ollama. Run: ollama serve"
                })
        
        self._send_json(response)
    
    def _check_ollama_status(self):
        """Legacy endpoint - redirects to _check_llm_status."""
        self._check_llm_status()

    def _handle_document_request(self, parsed):
        """Handle requests to load document content."""
        try:
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            path = query_params.get('path', [None])[0]
            
            if not path:
                self._send_json({"error": "No path specified"}, status=400)
                return
            
            # Security: ensure path is within DATA_DIR
            full_path = os.path.join(BASE_DIR, path)
            full_path = os.path.abspath(full_path)
            
            if not full_path.startswith(BASE_DIR):
                self._send_json({"error": "Access denied"}, status=403)
                return
            
            # Check if file exists
            if not os.path.exists(full_path):
                self._send_json({"error": f"File not found: {path}"}, status=404)
                return
            
            # Read file content
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._send_json({
                    "path": path,
                    "content": content,
                    "size": len(content)
                })
            except UnicodeDecodeError:
                # Try with different encoding
                with open(full_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                self._send_json({
                    "path": path,
                    "content": content,
                    "size": len(content)
                })
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def _send_json(self, data, status=200):
        response = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(response))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        # Suppress common client disconnect messages
        msg = args[0] if args else ""
        if "Broken pipe" in str(msg) or "Connection reset" in str(msg):
            return  # Don't log client disconnects
        print(f"[SupportAgent] {args[0]}")
    
    def log_error(self, format, *args):
        # Filter out harmless client disconnect errors
        msg = str(args[0]) if args else ""
        if any(err in msg for err in ["Broken pipe", "Connection reset", "Connection aborted"]):
            return  # Don't log client disconnects as errors
        # Log actual errors
        print(f"[ERROR] {format % args}")


def main():
    PORT = 8080
    print("=" * 60)
    print("  Support AI Agent — Backend Server")
    print("  Microsoft Dynamics 365 Contact Center (CCaaS)")
    print("=" * 60)
    print(f"  Knowledge Graph : {len(NODES)} nodes, {len(EDGES)} edges")
    print(f"  Ollama Model    : {OLLAMA_MODEL}")
    print(f"  Server          : http://localhost:{PORT}")
    print(f"  Chat UI         : http://localhost:{PORT}/support_agent.html")
    print(f"  Graph Explorer  : http://localhost:{PORT}/graph_explorer.html")
    print(f"  API — Chat      : POST http://localhost:{PORT}/api/chat")
    print(f"  API — Health    : GET  http://localhost:{PORT}/api/health")
    print(f"  API — LLM Status : GET  http://localhost:{PORT}/api/llm-status")
    print(f"  API — Ollama     : GET  http://localhost:{PORT}/api/ollama-status (legacy)")
    print("=" * 60)
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)

    # Create threaded server to handle multiple requests simultaneously
    server = ThreadingHTTPServer(("", PORT), SupportAgentHandler)
    server.timeout = 1  # Socket timeout to allow Ctrl+C to work
    
    print(f"\n✓ Server started successfully (threaded mode)")
    print(f"✓ Listening on http://localhost:{PORT}")
    print("\nWaiting for requests...\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("  Shutting down server...")
        print("=" * 60)
    finally:
        server.server_close()
        print("  Server stopped.")
        print("=" * 60)


if __name__ == "__main__":
    main()
