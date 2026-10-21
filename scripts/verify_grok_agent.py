"""Compatibility entry point; only the Groq provider is supported."""
from verify_groq_agent import main

if __name__ == "__main__": raise SystemExit(main() or 0)
