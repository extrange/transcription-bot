from openai import AsyncOpenAI

from transcription_bot.settings import Settings

_MODEL_PROMPT = "{text}\nWrite detailed minutes for the above meeting."


async def generate_summary(transcript: str) -> str | None:
    """Generate minutes for the transcript."""
    client = AsyncOpenAI(api_key=Settings.OPENAI_API_KEY.get_secret_value())
    completion = await client.chat.completions.create(
        model=Settings.OPENAI_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": _MODEL_PROMPT.format(text=transcript),
            },
        ],
    )
    return completion.choices[0].message.content
