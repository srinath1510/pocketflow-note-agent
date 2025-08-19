"""
In-memory storage and storage paths
"""
from pathlib import Path

# Storage directories
NOTES_DIR = Path("data/notes")
BATCHES_DIR = Path("data/batches")
RESULTS_DIR = Path("data/results")

# Create directories
for dir_path in [NOTES_DIR, BATCHES_DIR, RESULTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# In-memory storage
notes_storage = []
batches_storage = []
threads_storage = {}  # user_id -> Dict[thread_id, thread_data]
active_threads = {}   # user_id -> active_thread_id
processing_results = []
processed_batches = set()
processed_bakes = set()
content_hashes = set()
last_bake_time = None

# Configuration
BAKE_THROTTLE_SECONDS = 10