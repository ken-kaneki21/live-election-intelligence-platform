import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def generate_election_summary(results_df, close_df, party_summary_df):
    """
    Generates AI election summary using Groq.
    The LLM only receives structured data, not raw HTML.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or api_key == "your_groq_api_key_here":
        return (
            "Groq API key is missing. Add your key inside the .env file as:\n\n"
            "GROQ_API_KEY=your_actual_key_here\n\n"
            "The dashboard works without AI. Only this summary feature needs the key."
        )

    client = Groq(api_key=api_key)

    party_summary = party_summary_df.to_dict(orient="records")
    close_contests = close_df.head(20).to_dict(orient="records")

    total_rows = len(results_df)
    states = results_df["state"].dropna().unique().tolist()
    parties = results_df["party"].dropna().unique().tolist()

    prompt = f"""
You are an election data analyst.

Rules:
- Use only the structured data provided.
- Do not invent numbers.
- Do not make unsupported political claims.
- Do not predict final winners unless status says Won.
- Keep the answer concise and analytical.

Data size:
{total_rows} rows

States covered:
{states}

Parties covered:
{parties}

Party summary:
{party_summary}

Close contests:
{close_contests}

Generate:
1. Current election trend
2. Party-wise observations
3. Close contests to watch
4. Data limitations
5. 5 bullet-point executive summary
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a careful election analytics assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI summary failed. Error: {str(e)}"