"""
Interactive RAG demo.

Run:  python main.py
Then type questions about the documents in the 'documents/' folder.
"""

from rag_pipeline import RAGPipeline


def main():
    rag = RAGPipeline(
        documents_dir="documents",
        chunk_size=300,
        overlap=50,
        top_k=3,
    )

    print("RAG is ready! Type your question (or 'quit' to exit).\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = rag.query(question)

        print(f"\nAnswer: {result['answer']}")
        print("\nSources used:")
        for i, src in enumerate(result["sources"], 1):
            print(f"  [{i}] {src['source']} (distance={src['distance']:.4f})")
        print("-" * 60)


if __name__ == "__main__":
    main()
