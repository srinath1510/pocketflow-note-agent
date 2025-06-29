"""
Lightweight Flask API Server for Smart Notes Extension
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import uuid
import threading
import time
from datetime import datetime, timezone
import logging
import os
import traceback
import sys
from pathlib import Path
import hashlib
from collections import defaultdict

from pipeline_orchestrator import PipelineOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Enable CORS for Chrome extension
CORS(app, origins=["chrome-extension://*", "http://localhost:*"])

app.config['DEBUG'] = True

# In-memory storage
notes_storage = []
batches_storage = []
processing_results = []

# Storage directories
NOTES_DIR = Path("data/notes")
BATCHES_DIR = Path("data/batches")
RESULTS_DIR = Path("data/results")

# Create directories
for dir_path in [NOTES_DIR, BATCHES_DIR, RESULTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

processed_batches = set()  # Track processed batch IDs
processed_bakes = set()    # Track processed bake IDs
content_hashes = set()     # Track content hashes
last_bake_time = None      # Track last bake time
BAKE_THROTTLE_SECONDS = 10 # Minimum seconds between bakes

try:
    pipeline_orchestrator = PipelineOrchestrator()
    logger.info("Pipeline orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pipeline orchestrator: {str(e)}")
    pipeline_orchestrator = None


def hash_content(content):
    """Create hash of content to detect duplicates"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def is_duplicate_content(note_content):
    """Check if content is duplicate"""
    content_hash = hash_content(note_content)
    if content_hash in content_hashes:
        return True
    content_hashes.add(content_hash)
    return False


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with detailed information"""
    logger.error(f"500 Internal Server Error: {error}")
    logger.error(traceback.format_exc())
    
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(error),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'debug': str(traceback.format_exc()) if app.debug else None
    }), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {e}")
    logger.error(traceback.format_exc())
    
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(e),
        'type': type(e).__name__,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'debug': str(traceback.format_exc()) if app.debug else None
    }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for extension connectivity"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "service": "smart-notes-api",
            "server_type": "Flask WSGI",
            "debug_mode": app.debug,
            "endpoints": {
                "health": "/api/health",
                "notes_batch": "/api/notes/batch",
                "bake": "/api/bake",
                "notes": "/api/notes",
                "batches": "/api/batches",
                "results": "/api/results"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get detailed server status"""
    try:
        return jsonify({
            'server': 'Smart Notes Flask API',
            'status': 'running',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'debug_mode': app.debug,
            'python_version': sys.version,
            'flask_env': os.environ.get('FLASK_ENV', 'development'),
            'stats': {
                'notes_in_memory': len(notes_storage),
                'batches_processed': len(batches_storage),
                'processing_results': len(processing_results)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/batch', methods=['POST'])
def receive_batch():
    """Receive a batch of notes from the extension"""
    try:
        logger.info("=== BATCH PROCESSING REQUEST ===")
        
        data = request.get_json()
        logger.info(f"Received data: {data}")
        
        if not data:
            logger.error("No JSON data provided")
            return jsonify({"error": "No JSON data provided"}), 400
            
        if 'notes' not in data:
            logger.error("No notes in batch")
            return jsonify({"error": "No notes in batch"}), 400
        
        batch_id = data.get('batch_id', str(uuid.uuid4()))

        if batch_id in processed_batches:
            logger.warning(f"Duplicate batch detected: {batch_id}")
            return jsonify({
                "success": True,
                "status": "duplicate",
                "batch_id": batch_id,
                "message": "Batch already processed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 200

        notes = data['notes']
        
        logger.info(f"Processing batch {batch_id} with {len(notes)} notes")

        unique_notes = []
        duplicate_count = 0
        
        for note in notes:
            note_content = note.get('content', '')
            if note_content and not is_duplicate_content(note_content):
                unique_notes.append(note)
            else:
                duplicate_count += 1
                logger.info(f"Skipping duplicate note: {note_content[:50]}...")
        
        logger.info(f"Filtered {duplicate_count} duplicates, processing {len(unique_notes)} unique notes")
        
        # Mark batch as processed
        processed_batches.add(batch_id)
        
        # Store batch metadata
        batch_info = {
            "batch_id": batch_id,
            "timestamp": data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            "batch_size": len(notes),
            "unique_notes": len(unique_notes),
            "duplicates_filtered": duplicate_count,
            "status": "received",
            "notes_count": len(unique_notes),
            "processing_mode": data.get('processing_mode', 'default')
        }
        
        # Save to file only if we got unique notes
        if unique_notes:
            batch_file = BATCHES_DIR / f"{batch_id}.json"
            with open(batch_file, 'w') as f:
                json.dump({
                    "batch_info": batch_info,
                    "notes": unique_notes
                }, f, indent=2)
            
            timestamped_notes = []
            for note in unique_notes:
                note['stored_at'] = datetime.now(timezone.utc).isoformat()
                timestamped_notes.append(note)
            
            # Store in memory for display
            notes_storage.extend(timestamped_notes)

            # Background file saving
            file_thread = threading.Thread(target=save_individual_notes_background, args=(unique_notes, batch_id))
            file_thread.daemon = True
            file_thread.start()
            
            # Process in background thread
            process_thread = threading.Thread(target=process_batch_background, args=(batch_id, unique_notes))
            process_thread.daemon = True
            process_thread.start()
        
        batches_storage.append(batch_info)
        
        logger.info(f"Batch {batch_id} queued for processing")
        
        response = {
            "success": True,
            "status": "success",
            "batch_id": batch_id,
            "notes_received": len(notes),
            "notes_processed": len(unique_notes),
            "duplicates_filtered": duplicate_count,
            "notes_count": len(unique_notes),
            "message": f"Batch received: {len(unique_notes)} unique notes, {duplicate_count} duplicates filtered",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Batch processing response: {response}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Error processing batch: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500


@app.route('/api/bake', methods=['POST'])
def trigger_bake():
    """Trigger the AI processing pipeline (bake) on collected notes"""
    global last_bake_time
    try:
        logger.info("=== BAKE REQUEST ===")

        current_time = datetime.now(timezone.utc)
        
        if last_bake_time is not None:
            time_diff = (current_time - last_bake_time).total_seconds()
            if time_diff < BAKE_THROTTLE_SECONDS:
                wait_time = BAKE_THROTTLE_SECONDS - time_diff
                logger.warning(f"Bake throttled. {wait_time:.1f} seconds remaining.")
                return jsonify({
                    "success": False,
                    "error": f"Please wait {wait_time:.1f} seconds before starting another bake.",
                    "throttle_remaining": wait_time,
                    "timestamp": current_time.isoformat()
                }), 429  # Too Many Requests
        
        data = request.get_json() or {}
        logger.info(f"Bake data: {data}")
        
        bake_id = data.get('bake_id', str(uuid.uuid4()))

        if bake_id in processed_bakes:
            logger.warning(f"Duplicate bake detected: {bake_id}")
            return jsonify({
                "success": True,
                "status": "duplicate",
                "bake_id": bake_id,
                "message": "Bake already processed",
                "timestamp": current_time.isoformat()
            }), 200

        # Mark bake as processed
        processed_bakes.add(bake_id)
        last_bake_time = current_time
        
        # Prepare bake data
        bake_data = {
            "bake_id": bake_id,
            "timestamp": data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            "source": data.get('source', data.get('trigger_source', 'extension')),
            "include_additional_notes": data.get('includeAdditionalNotes', False),
            "additional_notes": data.get('additionalNotes', ''),
            "total_notes": len(notes_storage),
            "status": "initiated"
        }
        
        # Save bake request
        bake_file = RESULTS_DIR / f"bake_{bake_id}.json"
        with open(bake_file, 'w') as f:
            json.dump(bake_data, f, indent=2)
        
        # Process in background thread
        thread = threading.Thread(target=process_bake_background, args=(bake_data,))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Bake {bake_id} initiated with {len(notes_storage)} notes")
        
        response = {
            "success": True,
            "status": "success",
            "bake_id": bake_id,
            "message": "Bake process initiated",
            "notes_count": len(notes_storage),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "bake_id": bake_id,
                "notes_count": len(notes_storage)
            }
        }
        
        logger.info(f"Bake result: {response}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error initiating bake: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Error initiating bake: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500


@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Get stored notes from memory (for popup display)"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        total = len(notes_storage)
        notes = notes_storage[offset:offset + limit]
        
        display_notes = []
        for i, note in enumerate(notes):
            display_note = {
                "id": note.get('id') or note.get('metadata', {}).get('local_id') or f"note_{offset + i}",
                "title": note.get('source', {}).get('title', 'Untitled'),
                "url": note.get('source', {}).get('url', ''),
                "content_preview": note.get('content', '')[:200] + ('...' if len(note.get('content', '')) > 200 else ''),
                "content_full": note.get('content', ''),
                "captured_at": note.get('metadata', {}).get('captured_at', 'unknown'),
                "stored_at": note.get('stored_at', 'unknown'),
                "category": note.get('metadata', {}).get('content_category', 'general'),
                "tags": note.get('metadata', {}).get('tags', []),
                "word_count": len(note.get('content', '').split()),
                "raw_note": note  # Full original note data
            }
            display_notes.append(display_note)

        return jsonify({
            "notes": display_notes,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            },
            "stats": {
                "total_notes": total,
                "returned": len(display_notes),
                "memory_usage": "display_optimized"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error retrieving notes: {str(e)}")
        return jsonify({"error": f"Error retrieving notes: {str(e)}"}), 500


@app.route('/api/batches', methods=['GET'])
def get_batches():
    """Get batch processing history"""
    try:
        return jsonify({
            "batches": batches_storage,
            "total_batches": len(batches_storage),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error retrieving batches: {str(e)}")
        return jsonify({"error": f"Error retrieving batches: {str(e)}"}), 500


@app.route('/api/results', methods=['GET'])
def get_results():
    """Get processing results"""
    try:
        return jsonify({
            "results": processing_results,
            "total_results": len(processing_results),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        return jsonify({"error": f"Error retrieving results: {str(e)}"}), 500


@app.route('/api/notes', methods=['DELETE'])
def clear_notes():
    """Clear all stored notes (for testing)"""
    try:
        global notes_storage
        notes_storage = []
        logger.info("All notes cleared")
        return jsonify({
            "status": "success", 
            "message": "All notes cleared",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Error clearing notes: {str(e)}")
        return jsonify({"error": f"Error clearing notes: {str(e)}"}), 500


@app.route('/api/cleanup', methods=['POST'])
def cleanup_data():
    """Clean up old processed IDs and duplicate tracking"""
    global processed_batches, processed_bakes, content_hashes
    
    try:
        # Keep only recent IDs (last 1000 each)
        if len(processed_batches) > 1000:
            processed_batches = set(list(processed_batches)[-500:])
        
        if len(processed_bakes) > 1000:
            processed_bakes = set(list(processed_bakes)[-500:])
        
        if len(content_hashes) > 5000:
            content_hashes = set(list(content_hashes)[-2500:])
        
        logger.info("Cleanup completed")
        
        return jsonify({
            "success": True,
            "message": "Cleanup completed",
            "stats": {
                "processed_batches": len(processed_batches),
                "processed_bakes": len(processed_bakes),
                "content_hashes": len(content_hashes)
            }
        })
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        'message': 'Smart Notes Flask API',
        'version': '1.0.0',
        'server_type': 'Flask WSGI',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'pipeline_status': 'available' if pipeline_orchestrator else 'unavailable',
        'endpoints': {
            'health': '/api/health',
            'status': '/api/status',
            'notes_batch': '/api/notes/batch',
            'bake': '/api/bake',
            'notes': '/api/notes',
            'batches': '/api/batches',
            'results': '/api/results'
        }
    })


@app.route('/api/notes/files', methods=['GET'])
def get_notes_files_info():
    """Get information about stored note files (utility endpoint)"""
    try:
        note_files = list(NOTES_DIR.glob("note_*.json"))
        
        file_info = []
        for note_file in note_files:
            file_info.append({
                "filename": note_file.name,
                "size_bytes": note_file.stat().st_size,
                "created_at": datetime.fromtimestamp(note_file.stat().st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(note_file.stat().st_mtime).isoformat()
            })
        
        return jsonify({
            "file_count": len(file_info),
            "files": file_info,
            "total_size_bytes": sum(f["size_bytes"] for f in file_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        return jsonify({"error": f"Error getting file info: {str(e)}"}), 500


def process_batch_background(batch_id, notes):
    """Background processing of a batch of notes"""
    logger.info(f"Processing batch {batch_id} in background")
    
    try:
        # Simulate processing time
        time.sleep(2)
        
        # TODO: Integrate with your main.py pipeline here
        processed_notes = []
        for note in notes:
            processed_note = {
                "original": note,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processing_status": "completed",
                "insights": f"Processed note from {note.get('source', {}).get('url', 'unknown')}",
                "categories": [note.get('metadata', {}).get('content_category', 'general')],
            }
            processed_notes.append(processed_note)
        
        # Update batch status
        batch_result = {
            "batch_id": batch_id,
            "status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "notes_processed": len(processed_notes),
            "results": processed_notes
        }
        
        # Save results
        result_file = BATCHES_DIR / f"{batch_id}_result.json"
        with open(result_file, 'w') as f:
            json.dump(batch_result, f, indent=2)
        
        logger.info(f"Batch {batch_id} processing completed")
        
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {str(e)}")
        logger.error(traceback.format_exc())

def process_bake_background(bake_data):
    """Background processing of bake request"""
    bake_id = bake_data['bake_id']
    logger.info(f"Processing bake {bake_id} in background")
    
    try:
        if not pipeline_orchestrator:
            raise Exception("Pipeline orchestrator not available")
        
        session_notes = []
        for note in notes_storage:
            display_note = {
                "id": note.get('id') or note.get('metadata', {}).get('local_id') or f"note_{len(session_notes)}",
                "title": note.get('source', {}).get('title', 'Untitled'),
                "url": note.get('source', {}).get('url', ''),
                "content_full": note.get('content', ''),
                "captured_at": note.get('metadata', {}).get('captured_at', 'unknown'),
                "stored_at": note.get('stored_at', 'unknown'),
                "raw_note": note
            }
            session_notes.append(display_note)
        
        logger.info(f"Running pipeline on {len(session_notes)} notes for bake {bake_id}")

        pipeline_results = pipeline_orchestrator.run_pipeline(bake_data, session_notes)

        processing_results.append(pipeline_results)

        result_file = RESULTS_DIR / f"bake_{bake_id}_pipeline_result.json"
        with open(result_file, 'w') as f:
            json.dump(pipeline_results, f, indent=2, default=str)
        
        summary_result = {
            "bake_id": bake_id,
            "status": pipeline_results.get('status', 'unknown'),
            "processed_at": pipeline_results.get('processed_at'),
            "input_notes_count": pipeline_results.get('input_notes_count', 0),
            "processing_summary": pipeline_results.get('processing_summary', {}),
            "insights": pipeline_results.get('insights', []),
            "results_summary": pipeline_results.get('results', {}),
            "pipeline_metadata": {
                "session_id": pipeline_results.get('pipeline_metadata', {}).get('session_id'),
                "execution_time": pipeline_results.get('pipeline_metadata', {}).get('execution_time'),
                "nodes_executed": pipeline_results.get('pipeline_metadata', {}).get('nodes_executed', [])
            }
        }
        
        summary_file = RESULTS_DIR / f"bake_{bake_id}_summary.json"

        with open(summary_file, 'w') as f:
            json.dump(summary_result, f, indent=2, default=str)
        
        logger.info(f"Pipeline bake {bake_id} completed successfully")
        logger.info(f"Processed {pipeline_results.get('input_notes_count', 0)} notes")
        logger.info(f"Generated {len(pipeline_results.get('insights', []))} insights")
                
    except Exception as e:
        logger.error(f"Error processing bake {bake_id}: {str(e)}")
        logger.error(traceback.format_exc())

        error_result = {
            "bake_id": bake_id,
            "status": "failed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "input_notes_count": len(notes_storage),
            "error": str(e),
            "error_type": type(e).__name__,
            "pipeline_metadata": {
                "error_occurred": True,
                "nodes_executed": []
            }
        }

        processing_results.append(error_result)
        
        error_file = RESULTS_DIR / f"bake_{bake_id}_error.json"
        with open(error_file, 'w') as f:
            json.dump(error_result, f, indent=2, default=str)

        

def save_individual_notes_background(notes, batch_id):
    """Save individual notes to files in background (for persistence)"""
    try:
        logger.info(f"Background saving {len(notes)} notes to files")
        
        for i, note in enumerate(notes):
            note_id = note.get('id') or note.get('metadata', {}).get('local_id') or f"{batch_id}_note_{i}"
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
            note_filename = f"note_{timestamp}_{note_id}.json"
            note_file = NOTES_DIR / note_filename
            
            note_data = {
                "note_id": note_id,
                "batch_id": batch_id,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "source": note.get('source', {}),
                "metadata": note.get('metadata', {}),
                "content": note.get('content', ''),
                "original_note": note
            }
            
            # Save individual note
            with open(note_file, 'w') as f:
                json.dump(note_data, f, indent=2)
            
        logger.info(f"Background file save completed for batch {batch_id}")
            
    except Exception as e:
        logger.error(f"Error in background file saving: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Smart Notes Flask API Server...")
    print("📊 Server will run on: http://localhost:8000")
    print("🔧 Health check: http://localhost:8000/api/health")
    print("🔍 Debug mode: ENABLED")
    print("📍 Available endpoints:")
    print("  - GET  /              (Root)")
    print("  - GET  /api/health    (Health check)")
    print("  - GET  /api/status    (Status)")
    print("  - POST /api/notes/batch (Process notes)")
    print("  - POST /api/bake      (Bake notes)")
    print("  - GET  /api/notes     (Get notes)")
    print("  - GET  /api/batches   (Get batches)")
    print("  - GET  /api/results   (Get results)")
    print("  - DELETE /api/notes   (Clear notes)")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    app.run(
        host="localhost",  # Changed from "0.0.0.0" for local development
        port=8000, 
        debug=True, 
        threaded=True,
        use_reloader=True,
        use_debugger=True
    )