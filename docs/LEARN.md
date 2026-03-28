# Learning Resources for DoqToq

This curated collection of papers, articles, and resources provides essential knowledge for understanding and contributing to DoqToq - an expressive Retrieval-Augmented Generation (RAG) system that transforms documents into engaging conversational partners.

## Table of Contents
- [Retrieval-Augmented Generation (RAG)](#retrieval-augmented-generation-rag)
- [AI Agents](#ai-agents)
- [Vector Databases & Search](#vector-databases--search)
- [Programming Frameworks](#programming-frameworks)
- [Conversational AI & Personality](#conversational-ai--personality)
- [Blog Posts and Articles](#blog-posts-and-articles)
- [Getting Started](#getting-started)

---

## Retrieval-Augmented Generation (RAG)

### Foundational Papers
- **"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)** - [arXiv](https://arxiv.org/abs/2005.11401)
  - The original RAG paper that introduced the concept and demonstrated how combining retrieval with generation improves factual accuracy

- **"Realm: Retrieval-Augmented Language Model Pre-Training" (Guu et al., 2020)** - [arXiv](https://arxiv.org/abs/2002.08909)
  - Shows how to integrate retrieval during pre-training rather than just fine-tuning

- **"Dense Passage Retrieval for Open-Domain Question Answering" (Karpukhin et al., 2020)** - [arXiv](https://arxiv.org/abs/2004.04906)
  - Foundational work on dense retrieval that underlies many RAG systems

### Advanced RAG Techniques
- **"FiD: Leveraging Passage Retrieval with Generative Models" (Izacard & Grave, 2021)** - [arXiv](https://arxiv.org/abs/2007.01282)
  - Fusion-in-Decoder approach that processes multiple retrieved passages independently before fusion

- **"REPLUG: Retrieval-Augmented Black-Box Language Models" (Shi et al., 2023)** - [arXiv](https://arxiv.org/abs/2301.12652)
  - Framework that treats language models as black boxes while augmenting them with tunable retrieval

- **"Self-RAG: Learning to Critique and Correct through Self-Reflection" (Asai et al., 2023)** - [arXiv](https://arxiv.org/abs/2310.11511)
  - Introduces self-reflection mechanisms to improve RAG quality

- **"RETRO: Improving Language Models by Retrieving from Trillions of Tokens" (Borgeaud et al., 2022)** - [arXiv](https://arxiv.org/abs/2112.04426)
  - DeepMind's approach to scaling retrieval-augmented language models

### Evaluation and Analysis
- **"Rethinking the Role of Demonstrations: What Makes In-Context Learning Work?" (Min et al., 2022)** - [arXiv](https://arxiv.org/abs/2202.12837)
  - Important for understanding retrieval selection strategies

---

## AI Agents

### Foundational Agent Papers
- **"ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)** - [arXiv](https://arxiv.org/abs/2210.03629)
  - Introduces the ReAct paradigm combining reasoning traces with actions, fundamental to many current agent frameworks

- **"Toolformer: Language Models Can Teach Themselves to Use Tools" (Schick et al., 2023)** - [arXiv](https://arxiv.org/abs/2302.04761)
  - Shows how language models can learn to use external tools through self-supervision

- **"Chain of Tools: Large Language Models as Tool Makers" (Qian et al., 2023)** - [arXiv](https://arxiv.org/html/2405.16533v1)
  - Framework for LLMs to create and use custom tools for complex problem solving

### Planning and Search
- **"Tree of Thoughts: Deliberate Problem Solving with Large Language Models" (Yao et al., 2023)** - [arXiv](https://arxiv.org/abs/2305.10601)
  - Extends chain-of-thought to tree-structured exploration for complex problem solving

- **"Language Agent Tree Search: Large Language Models as Search Trees" (Zhou et al., 2023)** - [arXiv](https://arxiv.org/abs/2310.04406)
  - Novel approach using tree search algorithms to improve language model reasoning and decision-making

- **"Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning" (Wang et al., 2023)** - [arXiv](https://arxiv.org/abs/2305.04091)
  - Systematic approach to planning in language model reasoning

### Multi-Agent Systems
- **"Communicative Agents for Software Development" (Qian et al., 2023)** - [arXiv](https://arxiv.org/abs/2307.07924)
  - ChatDev paper showing multi-agent collaboration for complex software development tasks

- **"MetaGPT: Meta Programming for Multi-Agent Collaborative Framework" (Hong et al., 2023)** - [arXiv](https://arxiv.org/abs/2308.00352)
  - Framework for coordinating multiple specialized agents

- **"AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation" (Wu et al., 2023)** - [arXiv](https://arxiv.org/abs/2308.08155)
  - Microsoft's framework for building conversational multi-agent systems

### Memory and Learning
- **"Generative Agents: Interactive Simulacra of Human Behavior" (Park et al., 2023)** - [arXiv](https://arxiv.org/abs/2304.03442)
  - Stanford's work on agents with memory, planning, and social behaviors

- **"MemGPT: Towards LLMs as Operating Systems" (Packer et al., 2023)** - [arXiv](https://arxiv.org/abs/2310.08560)
  - Introduces hierarchical memory management for long-term agent interactions

- **"Reflexion: Language Agents with Verbal Reinforcement Learning" (Shinn et al., 2023)** - [arXiv](https://arxiv.org/abs/2303.11366)
  - Self-reflection and learning from mistakes in agent behavior

### Code and Tool Use
- **"Code as Policies: Language Model Programs for Embodied Control" (Liang et al., 2022)** - [arXiv](https://arxiv.org/abs/2209.07753)
  - Using LLMs to generate executable code for robotic control

- **"Gorilla: Large Language Model Connected with Massive APIs" (Patil et al., 2023)** - [arXiv](https://arxiv.org/abs/2305.15334)
  - Training models to effectively use APIs and tools

- **"CodeAct: Executable Code Actions Elicit Better LLM Agents" (Wang et al., 2024)** - [arXiv](https://arxiv.org/abs/2402.01030)
  - Using code execution as the primary action space for agents

### Evaluation and Benchmarking
- **"AgentBench: Evaluating LLMs as Agents" (Liu et al., 2023)** - [arXiv](https://arxiv.org/abs/2308.03688)
  - Comprehensive benchmark for evaluating agent capabilities across multiple domains

- **"WebArena: A Realistic Web Environment for Building Autonomous Agents" (Zhou et al., 2023)** - [arXiv](https://arxiv.org/abs/2307.13854)
  - Realistic web-based environment for testing agent capabilities

---

## Vector Databases & Search

### Core Search Technologies
- **"Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs" (Malkov & Yashunin, 2018)** - [arXiv](https://arxiv.org/abs/1603.09320)
  - The HNSW algorithm that powers many modern vector databases for efficient similarity search

- **"Faiss: A Library for Efficient Similarity Search" (Johnson et al., 2017)** - [arXiv](https://arxiv.org/abs/1702.08734)
  - Facebook's library for efficient similarity search and clustering of dense vectors

### Vector Database Applications
- **"Dense Passage Retrieval for Open-Domain Question Answering" (Karpukhin et al., 2020)** - [arXiv](https://arxiv.org/abs/2004.04906)
  - Foundational work on using dense vector representations for document retrieval

- **"Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks" (Reimers & Gurevych, 2019)** - [arXiv](https://arxiv.org/abs/1908.10084)
  - Essential for creating high-quality document embeddings for vector search

---

## Programming Frameworks

### Declarative AI Programming
- **"DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines" (Khattab et al., 2023)** - [arXiv](https://arxiv.org/abs/2310.03714)
  - Framework for programming language models declaratively rather than through prompting

### LLM Orchestration
- **"LangChain: Building Applications with LLMs through Composability"** - [GitHub](https://github.com/langchain-ai/langchain)
  - Popular framework for building LLM applications with modular components

- **"HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face" (Shen et al., 2023)** - [arXiv](https://arxiv.org/abs/2303.17580)
  - Framework for using LLMs as controllers to orchestrate multiple AI models

---

## Conversational AI & Personality

### Personality and Character Development
- **"Character-LLM: A Trainable Agent for Role-Playing" (Shao et al., 2023)** - [arXiv](https://arxiv.org/abs/2310.10158)
  - Methods for developing consistent character personalities in language models

- **"Large Language Models as Generalizable Policies for Embodied Tasks" (Szot et al., 2023)** - [arXiv](https://arxiv.org/abs/2310.17722)
  - Approaches to grounding language models in embodied environments and tasks

### Dialogue and Conversation
- **"BlenderBot 3: a deployed conversational agent that continually learns to responsibly engage" (Shuster et al., 2022)** - [arXiv](https://arxiv.org/abs/2208.03188)
  - Insights into building engaging, responsible conversational agents

- **"LaMDA: Language Models for Dialog Applications" (Thoppilan et al., 2022)** - [arXiv](https://arxiv.org/abs/2201.08239)
  - Google's approach to building dialogue-focused language models

### First-Person Perspective Systems
- **"Sparks of Artificial General Intelligence: Early Experiments with GPT-4" (Bubeck et al., 2023)** - [arXiv](https://arxiv.org/abs/2303.12712)
  - Comprehensive analysis including theory of mind capabilities in large language models

- **"Theory of Mind in Large Language Models: Assessment and Enhancement" (2025)** - [arXiv](https://arxiv.org/abs/2505.00026)
  - Review of LLMs' theory of mind capabilities and methods for improvement

---

## Blog Posts and Articles

### Vector Databases
1. **"An Introduction to Vector Databases"** - [Qdrant Blog](https://qdrant.tech/articles/what-is-a-vector-database/)
   - Comprehensive introduction to vector databases and their applications

2. **"The Rise of Vector Databases"** - [Pinecone Blog](https://www.pinecone.io/learn/vector-database/)
   - Industry perspective on vector database adoption and use cases

### RAG Implementation
3. **"Advanced RAG Techniques"** - [LlamaIndex Blog](https://blog.llamaindex.ai/a-cheat-sheet-and-some-recipes-for-building-advanced-rag-803a9d94c41b)
   - Practical guide to implementing advanced RAG patterns

### AI Agents
5. **"The Complete Guide to Building AI Agents"** - [LangChain Blog](https://blog.langchain.dev/what-is-an-agent/)
   - Comprehensive guide to building and deploying AI agents

6. **"DSPy: A New Paradigm for AI Programming"** - [DSPy Documentation](https://dspy.ai/)
   - Introduction to declarative AI programming with DSPy

## AI Research
1. **OpenAI Research** - [OpenAI Research](https://openai.com/research/)

2. **Anthropic Research** - [Anthropic Research](https://www.anthropic.com/research)

---

## Getting Started

### For New Contributors
1. **Start with the foundational RAG paper** (Lewis et al., 2020) to understand the core concepts
2. **Read the ReAct paper** (Yao et al., 2022) to understand agent reasoning patterns
3. **Explore vector database concepts** with the Qdrant introduction article
4. **Understand DSPy** for declarative AI programming approaches

### For Advanced Development
1. **Study REPLUG** for black-box LLM augmentation techniques
2. **Examine Language Agent Tree Search** for advanced reasoning strategies
3. **Review Generative Agents** for personality and memory implementation
4. **Explore Self-RAG** for self-improving retrieval systems

### Implementation Resources
- **DSPy Framework**: [dspy.ai](https://dspy.ai/) - For declarative AI programming
- **LangChain**: [python.langchain.com](https://python.langchain.com/) - For LLM application development
- **Vector Databases**: Qdrant, Pinecone, Weaviate for similarity search
- **Embedding Models**: Sentence Transformers, OpenAI embeddings for document representation

---

## Contributing to This Resource List 🤝

This is a living document! If you find papers, articles, or resources that would benefit the DoqToq community, please:

1. Verify the links are accurate and functional
2. Ensure the resource is highly relevant to RAG, agents, or conversational AI
3. Add a brief, informative description
4. Place it in the appropriate section
5. Submit a pull request with your additions

**Quality over quantity** - we aim to curate only the most valuable and relevant resources for building expressive RAG systems like DoqToq.

---

*Last updated: August 2025*
