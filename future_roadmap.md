ProfitGraph: Future Development Roadmap
Phase 4: Data Hygiene (The "Deduplication Agent")
Problem: As we ingest multiple videos about the same topic (e.g., 5 videos on "DeepSeek"), the Graph will create 5 separate "DeepSeek" nodes (DeepSeek, DeepSeek AI, Deep Seek), fragmenting knowledge.
Solution: A "Janitor" script that runs weekly.
Logic:
 * Query Neo4j for nodes with similar names (Fuzzy Matching).
 * Use Gemini to determine if they are the same entity.
 * Execute Cypher apoc.refactor.mergeNodes to combine them, preserving all relationships.
Phase 5: Cost Optimization (Batch & Cache)
Problem: As usage scales, API costs for Sonar and Gemini will rise.
Solution:
 * Context Caching: Cache the "Project Bible" system prompt in Gemini to reduce input token costs by ~90% for repeated tasks.
 * Batch API: Move the "Enrichment/Fact-Check" step to Gemini's Batch API (50% cheaper) for non-urgent videos, processing them overnight.
Phase 6: Multi-Modal Ingestion
Problem: Currently, we only read text (transcripts). We miss diagrams/code shown on screen.
Solution:
 * Use yt-dlp to capture screenshots at key timestamps.
 * Pass screenshots to Gemini 2.0 Flash (Multimodal) to extract architecture diagrams into Graph relationships ((System A)-[:ConnectsTo]->(System B)).
Phase 7: The "Agentic" UI
Problem: CLI is great for devs, but hard for quick referencing on the go.
Solution: A simple Streamlit interface (hosted on Streamlit Community Cloud for free) that connects to the Neo4j Aura instance, allowing you to generate plans from a web browser.

