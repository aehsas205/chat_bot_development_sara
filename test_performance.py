import time
import requests

API_URL = "http://127.0.0.1:8001/chat"

test_queries = [
    "What is AEHSAS Foundation?",
    "How can I contact the admin?",
    "Tell me about your vision and mission."
]

print("\n🚀 Starting Performance & Latency Benchmark...\n" + "="*50)

total_time = 0

for i, query in enumerate(test_queries, 1):
    start_time = time.time()
    
    payload = {"user_input": query, "session_id": f"perf_test_{i}"}
    response = requests.post(API_URL, json=payload)
    
    elapsed = time.time() - start_time
    total_time += elapsed
    
    status = "✅ PASS" if response.status_code == 200 else "❌ FAIL"
    print(f"Query {i}: '{query}'")
    print(f"Status: {status} | Latency: {elapsed:.2f} seconds\n")

avg_latency = total_time / len(test_queries)
