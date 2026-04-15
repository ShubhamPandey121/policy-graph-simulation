import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "policy_graph_db")

try:
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    simulations_collection = db["simulations"]
    print("✅ Connected to MongoDB successfully.")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    db = None
    simulations_collection = None

def save_simulation(data: dict):
    if simulations_collection is not None:
        try:
            result = simulations_collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error saving simulation: {e}")
    return None

def get_simulation_by_id(sim_id: str):
    if simulations_collection is not None:
        try:
            from bson.objectid import ObjectId
            return simulations_collection.find_one({"_id": ObjectId(sim_id)})
        except Exception as e:
            print(f"❌ Error fetching simulation: {e}")
    return None

def get_all_simulations():
    if simulations_collection is not None:
        try:
            sims = list(simulations_collection.find().sort("createdAt", -1).limit(50))
            for sim in sims:
                sim["_id"] = str(sim["_id"])
            return sims
        except Exception as e:
            print(f"❌ Error fetching all simulations: {e}")
    return []

def update_simulation_chat(sim_id: str, chat_history: list):
    if simulations_collection is not None:
        try:
            from bson.objectid import ObjectId
            simulations_collection.update_one(
                {"_id": ObjectId(sim_id)},
                {"$set": {"chatHistory": chat_history}}
            )
            return True
        except Exception as e:
            print(f"❌ Error updating chat history: {e}")
    return False

def delete_simulation(sim_id: str):
    if simulations_collection is not None:
        try:
            from bson.objectid import ObjectId
            simulations_collection.delete_one({"_id": ObjectId(sim_id)})
            return True
        except Exception as e:
            print(f"❌ Error deleting simulation: {e}")
    return False
