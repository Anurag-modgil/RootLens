import numpy as np
import logging
from app.services.embeddings import LogEmbeddingService

# Enable basic logging to stdout to see model initialization
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return dot_product / (norm_v1 * norm_v2)

def test_embeddings():
    print("--- Starting Embedding Service Test ---")
    
    # 1. Initialize Service
    service = LogEmbeddingService()
    
    # 2. Test Single Log Ingestion
    log1 = "Connection timeout while fetching user records from DB."
    vec1 = service.get_embedding(log1)
    
    print(f"\nSingle Log message: '{log1}'")
    print(f"Embedding Vector Dimension: {len(vec1)}")
    assert len(vec1) == 384, f"Expected 384 dimensions, got {len(vec1)}"
    print("Vector Dimension check passed.")
    
    # 3. Test Batch Ingestion
    logs = [
        "Database pool connection exhausted, failed to retrieve sessions.",
        "User auth succeeded for user_12345.",
        "Connection timeout while fetching session details from Database."
    ]
    
    vectors = service.get_embeddings(logs)
    print(f"\nBatch Log list size: {len(logs)}")
    print(f"Batch Vectors returned: {len(vectors)}")
    assert len(vectors) == len(logs), f"Expected {len(logs)} vectors, got {len(vectors)}"
    assert all(len(v) == 384 for v in vectors), "One or more batch vectors don't have 384 dimensions"
    print("Batch processing dimension check passed.")
    
    # 4. Verify Cosine Similarities (Semantic Consistency)
    sim_db_to_db = cosine_similarity(vectors[0], vectors[2])
    sim_db_to_auth = cosine_similarity(vectors[0], vectors[1])
    
    print(f"\nCosine Similarity [DB Issue 1 <-> DB Issue 2]: {sim_db_to_db:.4f}")
    print(f"Cosine Similarity [DB Issue 1 <-> Auth Success]: {sim_db_to_auth:.4f}")
    
    assert sim_db_to_db > sim_db_to_auth, "Semantic check failed: DB issue should be closer to DB issue than to auth success."
    print("Semantic similarity consistency check passed!")
    print("\n--- All Embedding Service Tests Passed! ---")

if __name__ == "__main__":
    test_embeddings()
