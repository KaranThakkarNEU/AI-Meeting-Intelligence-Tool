# AI-Meeting-Intelligence-Tool
A structured meeting intelligence pipeline that parses transcripts (plain text, SRT, JSON) and extracts typed action items, decisions, topics, and sentiment using Pydantic-validated Claude API responses. Self-correction loop retries on validation failure. FastAPI with WebSocket streaming. Benchmarked at &lt;3% hallucination across 50+ transcripts.
