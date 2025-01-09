from openai import OpenAI
import time

client = OpenAI(
    base_url='http://localhost:8000/v1',
    api_key='token-abc123',
)

s_time = time.time()
completion = client.chat.completions.create(
    model='google/gemma-2-27b-it',
    messages=[
            {"role" : "user", "content": "If you save $11,000 with an annual interest rate of 2.5% for a 5-year term, what is the final return?"},
    ]
    #max_tokens=1024,
    #extra_body={'use_beam_search': True, 'best_of': 10}
)

est_time = time.time() - s_time

print(completion.choices[0].message)
print(f'{est_time} s')