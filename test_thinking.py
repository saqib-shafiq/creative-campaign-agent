import asyncio
from cycls_agent import think_enhanced

async def test_thinking():
    # Test 1: Excited user with clear request
    messages = [{"role": "user", "content": "I'm so excited! Create a campaign for my new organic snack brand targeting health-conscious professionals in Riyadh!"}]
    
    decision = await think_enhanced(messages, messages[-1]["content"])
    print(f"Test 1 - Action: {decision.action}")
    print(f"Response: {decision.reply}\n")
    
    # Test 2: Frustrated user with vague request
    messages2 = [{"role": "user", "content": "This isn't working. Just make me a campaign already."}]
    
    decision2 = await think_enhanced(messages2, messages2[-1]["content"])
    print(f"Test 2 - Action: {decision2.action}")
    print(f"Response: {decision2.reply}\n")
    
    # Test 3: Confused user
    messages3 = [{"role": "user", "content": "I don't really understand how this works. Can you help?"}]
    
    decision3 = await think_enhanced(messages3, messages3[-1]["content"])
    print(f"Test 3 - Action: {decision3.action}")
    print(f"Response: {decision3.reply}")

if __name__ == "__main__":
    asyncio.run(test_thinking())