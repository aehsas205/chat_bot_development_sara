import time
from graph import chatmodel

# Pure Factual Accuracy Tests
test_cases = [
    {
        "query": "What is the fee for Lifetime Member?",
        "expected": "501"
    },
    {
        "query": "What is the fee for General Member?",
        "expected": "250"
    },
    {
        "query": "What is the fee for Patron Member?",
        "expected": "1001"
    }
]

print("🧪 Starting Pure Accuracy Test...\n" + "="*50)

for idx, case in enumerate(test_cases, 1):
    # Free tier API rate-limit se bachne ke liye wait
    if idx > 1:
        print("\n⏳ Waiting 20 seconds for API quota window...")
        time.sleep(20)
    
    state = {"messages": [{"content": case["query"]}]}
    try:
        res = chatmodel(state)
        answer = res["messages"][0].content
        
        print(f"\n[Test {idx}] Question: '{case['query']}'")
        print(f"🤖 Bot Answer: {answer[:180]}...")
        
        # Checking if expected figure is present in answer
        if case["expected"].lower() in answer.lower():
            print("Status: ✅ ACCURATE")
        else:
            print("Status: ❌ INACCURATE / MISSED INFO")
            
    except Exception as e:
        print(f"Status: ❌ ERROR ({e})")

print("\n" + "="*50 + "\nAccuracy Check Completed!")