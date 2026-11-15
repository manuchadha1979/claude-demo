from portkey_ai import Portkey
import os

portkey = Portkey(
    #api_key=os.environ["PORTKEY_DEMO_HELLO_WORLD_KEY"],
    api_key="HOlIpl4UixzlbAQtRhz5NbqpZY5X",
    metadata={"user_id": "manu_chadha", "_user": "manu_chadha", "source": "portkey-demo"}
)

response = portkey.chat.completions.create(
    model="@google/gemini-3.5-flash",
    messages=[
        {"role": "user", "content": "Hello from the Prisma AIRS demo."}
    ]
)

print(response.choices[0].message.content)