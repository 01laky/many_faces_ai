# How an AI model can “know more” — context, RAG, fine-tuning

The Ollama-served model (default `qwen2.5:7b-instruct-q4_K_M`) is **pre-trained** on a large general text corpus. It does **not** learn from our chat by itself — each call is stateless unless you add context. Three main ways to give it more information or adapt it:

---

## 1. Conversation context (within a session)

**What it is:** For each new message, send the model not only the latest user turn but also the **last N (user → assistant) pairs** as text. The model can then continue coherently.

**Pros:**

- No training, no weight updates
- Fast to implement (prompt formatting on the backend)
- Within one session it “remembers” prior turns

**Cons:**

- Memory only for that conversation; new chat = empty context
- Bounded length — only so many tokens fit in the prompt

**In this demo:** On `SendToAi`, the backend builds a prompt like `User: ...\nAI: ...\nUser: ...\nAI:` and calls `many_faces_ai`. The Python service converts that prompt to Ollama chat messages, optionally preserves operator statistics JSON as system context, calls Ollama, and returns only the new assistant fragment.

---

## 2. RAG (Retrieval-Augmented Generation)

**What it is:** A **knowledge base** (docs, FAQ, manuals). For each question:

1. Embed the question and query a **vector database**.
2. Retrieve **relevant chunks** from documents.
3. **Inject those chunks** into the prompt (e.g. “Given the following: … Answer: …”).
4. The model answers from that context — **weights unchanged**.

**Pros:**

- Ground answers in your documents without training
- Update the corpus without retraining

**Cons:**

- You need embeddings, vector DB, chunking strategy
- More moving parts (indexing, retrieval, prompt assembly)

---

## 3. Fine-tuning (train on your data)

**What it is:** Start from a pre-trained checkpoint and **continue training** on your dataset (Q/A pairs, dialogues, domain text). Weights **change permanently**; you ship a new checkpoint for inference.

**Pros:**

- Model can internalize domain and style
- Potentially more accurate and consistent with training data

**Cons:**

- Needs a quality dataset
- Compute (GPU), training time
- Data drift means retraining or lighter methods (LoRA, adapters)

---

## Summary

| Approach             | Weights change? | Memory / knowledge       | Effort |
| -------------------- | --------------- | ------------------------ | ------ |
| Conversation context | No              | Only in-session (prompt) | Low    |
| RAG                  | No              | Document corpus          | Medium |
| Fine-tuning          | Yes             | Baked into weights       | Higher |

This demo implements **conversation context** — the backend builds the prompt from recent turns, Python calls Ollama, and within one session the model follows the thread.
