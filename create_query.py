import asyncio
import time
from openai import OpenAI


async def send_request(idx: int):
    """Send a single request and return the response time."""
    client = OpenAI(
        base_url='http://localhost:8000/v1',
        api_key='token-abc123',
    )

    start_time = time.time()
    try:
        completion = client.chat.completions.create(
            model='google/gemma-2-27b-it',
            messages=[
                {"role": "user", "content": "If you save $11,000 with an annual interest rate of 2.5% for a 5-year term, what is the final return?"},
            ]
        )
        response_time = time.time() - start_time
        print(f"Request {idx}: {completion.choices[0].message} ({response_time:.2f} s)")
        return response_time
    except Exception as e:
        print(f"Request {idx} failed: {e}")
        return None

async def main(num_requests: int):
    """Send multiple requests concurrently and calculate statistics."""
    tasks = [asyncio.create_task(send_request(i + 1)) for i in range(num_requests)]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    # Filter out None results (failed requests)
    valid_times = [r for r in results if r is not None]

    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        first_request_time = valid_times[0]
        last_request_time = valid_times[-1]

        print("\nSummary:")
        print(f"Total time for {len(valid_times)} requests: {total_time:.2f} s")
        print(f"Average response time: {avg_time:.2f} s")
        print(f"First request response time: {first_request_time:.2f} s")
        print(f"Last request response time: {last_request_time:.2f} s")
    else:
        print("\nNo successful requests.")

# Number of requests to send
NUM_REQUESTS = 10

# Run the asyncio event loop
asyncio.run(main(NUM_REQUESTS))
