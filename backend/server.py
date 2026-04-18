import os
import re
import json
import pickle
import random
import tempfile
import time
import numpy as np
import pandas as pd
import faiss
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any
import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from duckduckgo_search import DDGS 
from textblob import TextBlob 
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from econml.dml import LinearDML
from sklearn.ensemble import RandomForestRegressor
from openai import OpenAI
from dotenv import load_dotenv

# Import database functions
from database import save_simulation, get_all_simulations, update_simulation_chat

try:
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_path
except ImportError:
    pass

load_dotenv()

NEO4J_URI = "neo4j+s://11283f72.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "fUj3kqKVq1rYniF_akSB-5aUq4pql2tg7Ux2vOC5MTg"
NEO4J_DATABASE = "neo4j"

# Cloud AI Provider Setup (OpenAI/Groq/DeepSeek)
# Using llama-3.1-8b-instant by default as it has a 128k context window, allowing for ~40+ page PDFs.
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1") # Default to Groq

ai_client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

MAX_WORKERS = 5

class AgentReport(BaseModel):
    role: str
    content: str
    diagram_code: Optional[str] = None
    diagram_json: Optional[List[Dict[str, Any]]] = None

class SimulationResponse(BaseModel):
    graph: Dict[str, Any]
    stats: Dict[str, Any]
    reports: List[AgentReport]
    metadata: Dict[str, Any]

class VisualizationEngine:
    @staticmethod
    def plot_causal_effect(effect, treatment_name, outcome_name):
        try:
            data = {
                'Scenario': ['Current Baseline', f'With +1 Unit {treatment_name}'],
                'Projected Growth': [100, 100 + (effect * 100)] 
            }
            df = pd.DataFrame(data)
            plt.figure(figsize=(8, 5))
            sns.set_theme(style="whitegrid")
            ax = sns.barplot(x='Scenario', y='Projected Growth', data=df, palette='viridis')
            plt.title(f"Causal Impact Analysis: {treatment_name} -> {outcome_name}", fontsize=14)
            plt.ylabel(f"Relative {outcome_name} Index (Baseline=100)")
            for i, v in enumerate(df['Projected Growth']):
                ax.text(i, v + 1, f"{v:.2f}", ha='center', fontweight='bold')
            os.makedirs("output", exist_ok=True)
            path = "output/causal_impact.png"
            plt.savefig(path)
            plt.close()
            return path
        except Exception:
            return None

class RLScraperAgent:
    def __init__(self, policy_file="data/rl_policy.json"):
        self.policy_file = policy_file
        self.ddgs = DDGS()
        self.strategies = [
            "official {topic} statistics India 2025",
            "{topic} government report data 2024-25",
            "economic impact of {topic} India analysis"
        ]
        self.q_table = self._load_policy()

    def _load_policy(self):
        if os.path.exists(self.policy_file):
            try:
                with open(self.policy_file, "r") as f: return json.load(f)
            except: pass
        return {s: 1.0 for s in self.strategies}

    def _save_policy(self):
        os.makedirs("data", exist_ok=True)
        with open(self.policy_file, "w") as f: json.dump(self.q_table, f)

    def get_strategy(self):
        if random.random() < 0.15: return random.choice(self.strategies)
        return max(self.q_table, key=self.q_table.get)

    def search_and_analyze(self, topic: str):
        strategy = self.get_strategy()
        query = strategy.format(topic=topic)
        print(f"🤖 [RL Monitor] Strategy: '{query}'")
        try:
            results = list(self.ddgs.text(query, max_results=3))
            if not results:
                self.q_table[strategy] -= 0.1
                self._save_policy()
                return None
            combined_text = "\n".join([r['body'] for r in results])
            sentiment = "Positive" if TextBlob(combined_text).sentiment.polarity > 0.1 else "Negative"
            if len(combined_text) > 100:
                self.q_table[strategy] += 0.2
                self._save_policy()
                return {"text": combined_text[:1000] + "...", "sentiment": sentiment, "source": query}
            return None
        except: return None

class CausalEngine:
    @staticmethod
    def run_inference(data_path="data/historical_stats.csv"):
        if not os.path.exists(data_path): return {"val": None, "msg": "No Data"}
        try:
            df = pd.read_csv(data_path)
            est = LinearDML(model_y=RandomForestRegressor(), model_t=RandomForestRegressor(), discrete_treatment=False)
            est.fit(df['sector_growth_pct'], df['funding_millions'], W=df[['inflation_rate', 'urban_pop_pct']])
            effect = est.effect(df[['inflation_rate', 'urban_pop_pct']]).mean()
            chart_path = VisualizationEngine.plot_causal_effect(effect, "Funding", "Sector Growth")
            return {
                "val": effect,
                "msg": f"Growth rises by {effect:.4f}% per $1M funding.",
                "chart": chart_path
            }
        except Exception as e: return {"val": None, "msg": f"Error: {e}"}

# ---------------- HELPER: MERMAID PARSER (CYTOSCAPE FORMAT) ----------------
def parse_mermaid_to_json(mermaid_code: str):
    if not mermaid_code:
        return []

    elements = []
    seen_ids = set()

    node_pattern = re.compile(r'([a-zA-Z0-9_]+)\s*\["?(.*?)"?\]')
    edge_pattern = re.compile(r'([a-zA-Z0-9_]+)\s*[-=.].*?>\s*([a-zA-Z0-9_]+)')

    lines = mermaid_code.split('\n')
    
    for line in lines:
        line = line.strip()
        
        node_matches = node_pattern.findall(line)
        for node_id, label in node_matches:
            if node_id not in seen_ids:
                clean_label = label.strip().strip('"').replace("<br>", " ")
                elements.append({
                    "group": "nodes",
                    "data": { "id": node_id, "label": clean_label }
                })
                seen_ids.add(node_id)

        edge_matches = edge_pattern.findall(line)
        for source, target in edge_matches:
            if source not in seen_ids:
                elements.append({ "group": "nodes", "data": {"id": source, "label": source} })
                seen_ids.add(source)
            
            if target not in seen_ids:
                elements.append({ "group": "nodes", "data": {"id": target, "label": target} })
                seen_ids.add(target)

            elements.append({
                "group": "edges",
                "data": { "source": source, "target": target }
            })

    return elements

# ---------------- COMPONENT 4: THE MAIN ENGINE (SMART UPDATE) ----------------
class PolicyGraphEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Hardware: {self.device.upper()} (RTX 4050)")
        
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device=self.device)
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        self.rl_agent = RLScraperAgent()
        self.causal_agent = CausalEngine()
        
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        self.index_path = "data/vector_store/faiss.index"
        self.meta_path = "data/vector_store/faiss_meta.pkl"
        
        self._ensure_statistical_data()

    def _ensure_statistical_data(self):
        path = "data/historical_stats.csv"
        if not os.path.exists(path):
            os.makedirs("data", exist_ok=True)
            np.random.seed(42)
            n = 1000
            funding = np.random.normal(100, 20, n)
            growth = 0.5 * funding + np.random.normal(0, 5, n)
            pd.DataFrame({
                'funding_millions': funding, 
                'sector_growth_pct': growth, 
                'inflation_rate': np.random.normal(5, 1, n), 
                'urban_pop_pct': np.random.normal(40, 5, n)
            }).to_csv(path, index=False)

    def close(self):
        self.driver.close()

    def ingest_pdfs(self, pdf_folder: str):
        if not os.path.exists(pdf_folder):
            return
        processed_files = self._get_processed_files()
        docs = []
        for file in os.listdir(pdf_folder):
            if file.endswith(".pdf"):
                if file in processed_files:
                    continue
                loader = PyPDFLoader(os.path.join(pdf_folder, file))
                for page in loader.load():
                    page.metadata["source_pdf"] = file
                    page.metadata["page_num"] = page.metadata.get("page", 0) + 1
                    docs.append(page)
        if not docs:
            return
        chunks = self.splitter.split_documents(docs)
        self._update_vector_store(chunks)
        self._sync_knowledge_graph_parallel(chunks)

    def _get_processed_files(self):
        try:
            with self.driver.session(database=NEO4J_DATABASE) as session:
                result = session.run("MATCH (d:Document) RETURN d.name AS name")
                return {record["name"] for record in result}
        except: return set()

    def _update_vector_store(self, new_chunks):
        texts = [c.page_content for c in new_chunks]
        embeddings = self.embedder.encode(texts, convert_to_numpy=True).astype("float32")
        meta = [{"text": c.page_content, "src": c.metadata["source_pdf"], "page": c.metadata["page_num"]} for c in new_chunks]
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            index = faiss.read_index(self.index_path)
            with open(self.meta_path, "rb") as f: metadata = pickle.load(f)
            index.add(embeddings)
            metadata.extend(meta)
        else:
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
            metadata = meta
        os.makedirs("data/vector_store", exist_ok=True)
        faiss.write_index(index, self.index_path)
        with open(self.meta_path, "wb") as f: pickle.dump(metadata, f)

    def _sync_knowledge_graph_parallel(self, chunks):
        batch_size = 5 
        batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self._process_graph_batch, batches)

    def _process_graph_batch(self, chunk_batch):
        combined_text = "EXTRACT DATA:\n"
        for i, c in enumerate(chunk_batch):
            combined_text += f"CHUNK {i}:\n{c.page_content[:1500]}\n---\n"
        data_list = self._ask_deepseek_batch(combined_text, len(chunk_batch))
        if data_list:
            with self.driver.session(database=NEO4J_DATABASE) as session:
                for i, data in enumerate(data_list):
                    if data and data.get("policy") and i < len(chunk_batch):
                        data["source_pdf"] = chunk_batch[i].metadata["source_pdf"]
                        data["page_num"] = chunk_batch[i].metadata["page_num"]
                        session.execute_write(self._write_cypher, data)

    def _ask_deepseek_batch(self, text: str, count: int):
        try:
            response = ai_client.chat.completions.create(
                model=MODEL_NAME,
                response_format={"type": "json_object"},
                messages=[
                    {'role': 'system', 'content': f"Extract policy data. Output ONLY JSON with the schema: {{'results': [{{'policy':str, 'year':int, 'affects':[str], 'ripples':[str]}}]}}"},
                    {'role': 'user', 'content': text}
                ]
            )
            return json.loads(response.choices[0].message.content).get("results", [])
        except Exception as e: 
            print("Error in ask_deepseek_batch:", e)
            return []

    @staticmethod
    def _write_cypher(tx, data):
        query = """
        MERGE (p:Policy {name: toUpper(trim($p_name))})
        SET p.year = $p_year
        MERGE (d:Document {name: $source_pdf})
        MERGE (p)-[:CITED_IN {page: $page_num}]->(d)
        WITH p
        UNWIND $sectors AS s_name
        MERGE (s1:Sector {name: toUpper(trim(s_name))})
        MERGE (p)-[:DIRECT_IMPACT]->(s1)
        WITH p, s1
        UNWIND $ripples AS r_name
        MERGE (s2:Sector {name: toUpper(trim(r_name))})
        MERGE (s1)-[:RIPPLE_EFFECT_TO]->(s2)
        """
        tx.run(query, p_name=str(data.get("policy", "Unknown")), p_year=int(data.get("year", 0)),
               source_pdf=data["source_pdf"], page_num=data["page_num"],
               sectors=data.get("affects", []), ripples=data.get("ripples", []))

    def analyze_input(self, *, query: Optional[str] = None, pdf: Optional[Any] = None, image: Optional[Any] = None):
        provided = [query, pdf, image]
        if sum(x is not None for x in provided) != 1:
            return {"error": "Provide exactly ONE input: query OR pdf OR image"}

        text = ""

        if query:
            text = query
        elif pdf:
            pdf_path = None
            try:
                import tempfile
                from pdf2image import convert_from_path
                import pytesseract
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf.file.read())
                    pdf_path = tmp.name

                loader = PyPDFLoader(pdf_path)
                pages = loader.load()
                text = "\n".join([p.page_content for p in pages])

                if len(text.strip()) < 50:
                    images = convert_from_path(pdf_path, dpi=300)
                    text = "\n".join(pytesseract.image_to_string(img) for img in images)

            except Exception as e:
                return {"error": f"PDF Processing Error: {str(e)}"}
            finally:
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
        elif image:
            img_path = None
            try:
                import tempfile
                from PIL import Image
                import pytesseract
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(image.file.read())
                    img_path = tmp.name

                text = pytesseract.image_to_string(Image.open(img_path))
            except Exception as e:
                return {"error": f"Image Processing Error: {str(e)}"}
            finally:
                if img_path and os.path.exists(img_path):
                    os.remove(img_path)

        if not text or not text.strip():
            return {"error": "No extraction possible. File might be blank or unreadable."}

        return self.analyze_ripple_effect_json(text)

    def analyze_ripple_effect_json(self, query: str):
        if not os.path.exists(self.index_path): 
            return {"error": "System not initialized. Please run ingestion first."}
        
        is_document_upload = len(query) > 500
        input_doc_context = ""
        
        if is_document_upload:
            print("📄 Document detected. Switching to Scrutinizer Mode.")
            input_doc_context = query
            lines = [l.strip() for l in query.split('\n') if l.strip()]
            search_query = lines[0][:100] if lines else "Policy Analysis"
        else:
            search_query = query

        print(f"⚙️ Running Simulation for: {search_query}")
        
        index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f: metadata = pickle.load(f)
        q_vec = self.embedder.encode([search_query]).astype("float32")
        _, I = index.search(q_vec, 10)
        raw_chunks = [metadata[i] for i in I[0]]
        scores = self.reranker.predict([[search_query, c['text']] for c in raw_chunks])
        top_chunks = [c for _, c in sorted(zip(scores, raw_chunks), key=lambda x: x[0], reverse=True)][:3]
        text_context = "\n".join([f"- {c['text']} (Source: {c['src']})" for c in top_chunks])
        
        graph_struct = self._get_graph_data_struct(search_query)
        graph_text_paths = [f"{e['source']} -> {e['target']}" for e in graph_struct['edges']]
        
        print("⏩ [System] RL Web Search skipped for speed.")
        live_data = {
            "text": "Live search disabled for local demo. Assuming stable policy environment.",
            "sentiment": "Neutral",
            "source": "Local_Override"
        }

        causal_insight = self.causal_agent.run_inference()
        
        full_context = {
            "NEW_POLICY_TEXT": input_doc_context if is_document_upload else "N/A",
            "HISTORICAL_CONTEXT": text_context,
            "LOGIC_CHAIN": graph_text_paths,
            "WEB_NEWS": live_data,
            "STATS": causal_insight
        }

        base_instruction = "Analyze context."
        if is_document_upload:
            base_instruction = f"CRITICAL: Scrutinize the NEW policy text (see 'NEW_POLICY_TEXT'). Predict ripple effects."
        else:
            base_instruction = f"Answer policy question: '{query}'."

        agents = {
            "Global Analyst": f"{base_instruction} Synthesize. Use 'LOGIC_CHAIN' to ground your reasoning. MANDATORY: You MUST include a '```mermaid' flowchart visualizing these flows.",
            "Real-Time Analyst": f"{base_instruction} (Standby Mode) Connect web trends if available. MANDATORY: You MUST include a '```mermaid' flowchart.",
            "Causal Scientist": f"{base_instruction} Validate assumptions against 'STATS'. MANDATORY: You MUST include a '```mermaid' flowchart.",
            "Economic Strategist": f"{base_instruction} Predict budget shifts across 4 waves (Curriculum, Faculty, Infra, Tech). MANDATORY: You MUST include a '```mermaid' flowchart.",
            "Social Advocate": f"{base_instruction} Trace impact on demographics using 'LOGIC_CHAIN' paths. MANDATORY: You MUST include a '```mermaid' flowchart."
        }
        
        results = {}
        for role, prompt in agents.items():
            print(f"🧠 Agent [{role}] is analyzing...")
            results[role] = self._call_cloud_model(role, prompt, query, full_context)
            time.sleep(2) # 2-second delay to help prevent rate-limits on free tiers

        processed_reports = []
        master_nodes = graph_struct['nodes'][:] 
        master_edges = graph_struct['edges'][:]

        for role in agents.keys():
            if role in results:
                content = results[role]
                raw_mermaid = ""
                agent_specific_elements = []

                if "```mermaid" in content:
                    parts = content.split("```mermaid")
                    try:
                        raw_mermaid = parts[1].split("```")[0].strip()
                        agent_specific_elements = parse_mermaid_to_json(raw_mermaid)
                    except Exception as e:
                        print(f"Mermaid Parse Error for {role}: {e}")
                    
                    cleaned_content = parts[0] + (parts[1].split("```")[-1] if "```" in parts[1] else "")
                else:
                    cleaned_content = content

                processed_reports.append({
                    "role": role,
                    "content": cleaned_content,
                    "diagram_code": raw_mermaid,
                    "diagram_json": agent_specific_elements 
                })
                
                for elem in agent_specific_elements:
                    if elem['group'] == 'nodes':
                        if not any(n['id'] == elem['data']['id'] for n in master_nodes):
                            master_nodes.append(elem['data'])
                            
                    elif elem['group'] == 'edges':
                        edge_data = {
                            "id": f"edge_{elem['data']['source']}_{elem['data']['target']}",
                            "source": elem['data']['source'],
                            "target": elem['data']['target'],
                            "label": "predicts"
                        }
                        master_edges.append(edge_data)

        return {
            "graph": {"nodes": master_nodes, "edges": master_edges},
            "stats": causal_insight,
            "reports": processed_reports, 
            "metadata": {
                "search_topic": search_query,
                "mode": "Scrutinization" if is_document_upload else "Policy Q&A"
            }
        }
    
    def _get_graph_data_struct(self, query):
        nodes = {} 
        edges = []
        try:
            with self.driver.session(database=NEO4J_DATABASE) as session:
                cypher = """
                MATCH (p:Policy)-[:DIRECT_IMPACT]->(s1:Sector)
                WHERE p.name CONTAINS toUpper($q) OR s1.name CONTAINS toUpper($q)
                OPTIONAL MATCH (s1)-[:RIPPLE_EFFECT_TO]->(s2:Sector)
                RETURN p.name as pol, s1.name as sec1, s2.name as sec2
                LIMIT 10
                """
                results = session.run(cypher, q=query[:6])
                for r in results:
                    if r['pol'] not in nodes: nodes[r['pol']] = {"id": r['pol'], "label": r['pol'], "type": "Policy"}
                    if r['sec1'] not in nodes: nodes[r['sec1']] = {"id": r['sec1'], "label": r['sec1'], "type": "Sector"}
                    edges.append({"source": r['pol'], "target": r['sec1'], "relation": "DIRECT_IMPACT"})
                    if r['sec2']:
                        if r['sec2'] not in nodes: nodes[r['sec2']] = {"id": r['sec2'], "label": r['sec2'], "type": "Sector"}
                        edges.append({"source": r['sec1'], "target": r['sec2'], "relation": "RIPPLE_EFFECT"})
        except Exception: pass
        return {"nodes": list(nodes.values()), "edges": edges}

    def _call_cloud_model(self, role, prompt, query, context):
        try:
            safe_context = context.copy()
            if "HISTORICAL_CONTEXT" in safe_context and len(safe_context["HISTORICAL_CONTEXT"]) > 15000:
                 safe_context["HISTORICAL_CONTEXT"] = safe_context["HISTORICAL_CONTEXT"][:15000] + "... [TRUNCATED]"

            response = ai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {'role': 'system', 'content': f"You are the {role}. {prompt} ALWAYS generate a mermaid.js block to visualize your findings."},
                    {'role': 'user', 'content': f"CONTEXT:\n{json.dumps(safe_context, indent=2)}\n\nINPUT: {query}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e: return f"Error: {e}"

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = None

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    context: Optional[str] = "" 
    sim_id: Optional[str] = None # Support saving chat history

@app.get("/simulations")
def get_simulations():
    """Fetch all saved simulations from MongoDB"""
    sims = get_all_simulations()
    return {"simulations": sims}

@app.post("/chat")
def chat_with_general_intelligence(req: ChatRequest):
    try:
        system_prompt = (
            "You are a highly intelligent AI assistant. Use your general knowledge "
            "and reasoning to answer the user. If context from a simulation is provided, "
            "reference it only if it is helpful and legible; otherwise, provide the best "
            "logical answer based on your internal training."
        )

        context_snippet = ""
        if req.context and len(req.context) > 100:
             context_snippet = f"\n[Optional Simulation Context]:\n{req.context[:5000]}"

        # Map history format for OpenAI
        messages = [{'role': 'system', 'content': system_prompt}]
        for msg in req.history:
            messages.append({'role': msg.get('role', 'user'), 'content': msg.get('content', '')})
            
        messages.append({'role': 'user', 'content': f"{context_snippet}\n\nUser Question: {req.message}"})

        response = ai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages
        )
        reply = response.choices[0].message.content
        
        # Save to MongoDB if sim_id provided
        if req.sim_id:
            new_history = req.history + [{'role': 'user', 'content': req.message}, {'role': 'assistant', 'content': reply}]
            update_simulation_chat(req.sim_id, new_history)

        return {"response": reply}
    except Exception as e:
        return {"response": f"I'm currently running on my core logic. API Error: {str(e)}"}

@app.on_event("startup")
async def startup_event():
    global engine
    try:
        print("🔧 Initializing PolicyGraphEngine... (This may take a moment)")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        engine = PolicyGraphEngine()
        print("✅ Engine Initialized and Ready.")
    except Exception as e:
        print(f"❌ Engine Initialization Failed: {e}")

@app.post("/analyze")
def analyze_endpoint(
    query: Optional[str] = Form(None),
    pdf: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None)
):
    if not engine:
        raise HTTPException(status_code=503, detail="Brain is still warming up. Please wait.")
    
    try:
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        
        result = engine.analyze_input(query=query, pdf=pdf, image=image)

        if torch.cuda.is_available(): torch.cuda.empty_cache()

        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Save to MongoDB
        sim_data = {
            "title": query[:60] + "..." if query and len(query) > 60 else (query or "Document Analysis"),
            "simulationData": result,
            "chatHistory": [],
            "createdAt": pd.Timestamp.now().isoformat(),
            "updatedAt": pd.Timestamp.now().isoformat()
        }
        
        sim_id = save_simulation(sim_data)
        if sim_id:
            result["_id"] = sim_id

        return result
    except Exception as e:
         if torch.cuda.is_available(): torch.cuda.empty_cache()
         raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Starting Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)