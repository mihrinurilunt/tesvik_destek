import os

# Deterministic test configuration. No live API calls are made by this suite.
os.environ['OPENAI_API_KEY'] = 'offline-test-not-a-real-key'
os.environ['QDRANT_URL'] = 'http://localhost:6333'
os.environ['QDRANT_COLLECTION_NAME'] = 'tesvikler_v2'
os.environ['QDRANT_VECTOR_NAME'] = 'text-dense'
