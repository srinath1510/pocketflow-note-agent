"""
Legacy endpoints (/api/notes, /api/bake)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import uuid
import json
import logging
import traceback
from typing import Optional
from pathlib import Path

from ..models.capture import BatchRequest, BakeRequest
from ..models.responses import BatchResponse, BakeResponse, NotesResponse, PaginationInfo
from ..utils.storage import (
    notes_storage, batches_storage, processing_results, processed_batches, 
    processed_bakes, content_hashes, last_bake_time, BAKE_THROTTLE_SECONDS,
    NOTES_DIR, BATCHES_DIR, RESULTS_DIR
)
from ..utils.helpers import hash_content, is_duplicate_content, serialize_for_json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/notes/batch", response_model=BatchResponse)
async def receive_batch(batch_request: BatchRequest, background_tasks: BackgroundTasks):
    """Receive a batch of notes from the extension"""
    try:
        logger.info("=== BATCH PROCESSING REQUEST ===")
        
        batch_id = batch_request.batch_id or str(uuid.uuid4())
        notes = batch_request.notes
        
        # Check for duplicate batch
        if batch_id in processed_batches:
            logger.warning(f"Duplicate batch detected: {batch_id}")
            return BatchResponse(
                success=True,
                status="duplicate",
                batch_id=batch_id,
                notes_received=len(notes),
                notes_processed=0,
                duplicates_filtered=0,
                message="Batch already processed",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        logger.info(f"Processing batch {batch_id} with {len(notes)} notes")
        
        # Filter duplicates
        unique_notes = []
        duplicate_count = 0
        
        for note in notes:
            note_content = note.content
            if note_content and not is_duplicate_content(note_content):
                # Convert Pydantic model to dict for processing
                note_dict = {
                    "content": note.content,
                    "user_id": note.user_id,
                    "source_url": note.source_url,
                    "title": note.title,
                    "timestamp": note.timestamp,
                    "intent": note.intent,
                    "user_note": note.user_note
                }
                
                # Handle legacy fields
                if note.source:
                    note_dict["source"] = {
                        "url": note.source.url,
                        "title": note.source.title,
                        "domain": note.source.domain
                    }
                
                if note.metadata:
                    note_dict["metadata"] = {
                        "content_category": note.metadata.content_category,
                        "captured_at": note.metadata.captured_at,
                        "tags": note.metadata.tags,
                        "local_id": note.metadata.local_id
                    }
                
                unique_notes.append(note_dict)
            else:
                duplicate_count += 1
                logger.info(f"Skipping duplicate note: {note_content[:50]}...")
        
        logger.info(f"Filtered {duplicate_count} duplicates, processing {len(unique_notes)} unique notes")
        
        # Mark batch as processed
        processed_batches.add(batch_id)
        
        # Store batch metadata
        batch_info = {
            "batch_id": batch_id,
            "timestamp": batch_request.timestamp or datetime.now(timezone.utc).isoformat(),
            "batch_size": len(notes),
            "unique_notes": len(unique_notes),
            "duplicates_filtered": duplicate_count,
            "status": "received",
            "notes_count": len(unique_notes),
            "processing_mode": batch_request.processing_mode
        }
        
        # Save and process if we have unique notes
        if unique_notes:
            # Save to file
            batch_file = BATCHES_DIR / f"{batch_id}.json"
            with open(batch_file, 'w') as f:
                json.dump({
                    "batch_info": batch_info,
                    "notes": unique_notes
                }, f, indent=2)
            
            # Add timestamps and store in memory
            timestamped_notes = []
            for note in unique_notes:
                note['stored_at'] = datetime.now(timezone.utc).isoformat()
                timestamped_notes.append(note)
            
            notes_storage.extend(timestamped_notes)
            
            # Process in background
            background_tasks.add_task(save_individual_notes_background, unique_notes, batch_id)
            background_tasks.add_task(process_batch_background, batch_id, unique_notes)
        
        batches_storage.append(batch_info)
        
        logger.info(f"Batch {batch_id} queued for processing")
        
        return BatchResponse(
            success=True,
            status="success",
            batch_id=batch_id,
            notes_received=len(notes),
            notes_processed=len(unique_notes),
            duplicates_filtered=duplicate_count,
            message=f"Batch received: {len(unique_notes)} unique notes, {duplicate_count} duplicates filtered",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/bake", response_model=BakeResponse)
async def trigger_bake(bake_request: BakeRequest, background_tasks: BackgroundTasks):
    """Trigger the AI processing pipeline (bake) on collected notes"""
    global last_bake_time
    
    try:
        logger.info("=== BAKE REQUEST ===")
        
        current_time = datetime.now(timezone.utc)
        
        # Throttle check
        if last_bake_time is not None:
            time_diff = (current_time - last_bake_time).total_seconds()
            if time_diff < BAKE_THROTTLE_SECONDS:
                wait_time = BAKE_THROTTLE_SECONDS - time_diff
                logger.warning(f"Bake throttled. {wait_time:.1f} seconds remaining.")
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {wait_time:.1f} seconds before starting another bake."
                )
        
        bake_id = bake_request.bake_id or str(uuid.uuid4())
        
        # Check for duplicate bake
        if bake_id in processed_bakes:
            logger.warning(f"Duplicate bake detected: {bake_id}")
            return BakeResponse(
                success=True,
                status="duplicate",
                bake_id=bake_id,
                message="Bake already processed",
                notes_count=len(notes_storage),
                timestamp=current_time.isoformat()
            )
        
        # Mark bake as processed
        processed_bakes.add(bake_id)
        last_bake_time = current_time
        
        # Prepare bake data
        bake_data = {
            "bake_id": bake_id,
            "timestamp": bake_request.timestamp or datetime.now(timezone.utc).isoformat(),
            "source": bake_request.source or bake_request.trigger_source,
            "include_additional_notes": bake_request.includeAdditionalNotes,
            "additional_notes": bake_request.additionalNotes,
            "total_notes": len(notes_storage),
            "status": "initiated"
        }
        
        # Save bake request
        bake_file = RESULTS_DIR / f"bake_{bake_id}.json"
        with open(bake_file, 'w') as f:
            json.dump(bake_data, f, indent=2)
        
        # Process in background
        background_tasks.add_task(process_bake_background, bake_data)
        
        logger.info(f"Bake {bake_id} initiated with {len(notes_storage)} notes")
        
        return BakeResponse(
            success=True,
            status="success",
            bake_id=bake_id,
            message="Bake process initiated",
            notes_count=len(notes_storage),
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={
                "bake_id": bake_id,
                "notes_count": len(notes_storage)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating bake: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error initiating bake: {str(e)}"
        )


@router.get("/notes", response_model=NotesResponse)
async def get_notes(
    limit: int = Query(50, ge=1, le=1000, description="Number of notes to return"),
    offset: int = Query(0, ge=0, description="Number of notes to skip")
):
    """Get stored notes from memory (for popup display)"""
    try:
        total = len(notes_storage)
        notes = notes_storage[offset:offset + limit]
        
        display_notes = []
        for i, note in enumerate(notes):
            display_note = {
                "id": note.get('id') or note.get('metadata', {}).get('local_id') or f"note_{offset + i}",
                "title": note.get('source', {}).get('title', note.get('title', 'Untitled')),
                "url": note.get('source', {}).get('url', note.get('source_url', '')),
                "content_preview": note.get('content', '')[:200] + ('...' if len(note.get('content', '')) > 200 else ''),
                "content_full": note.get('content', ''),
                "captured_at": note.get('metadata', {}).get('captured_at', note.get('timestamp', 'unknown')),
                "stored_at": note.get('stored_at', 'unknown'),
                "category": note.get('metadata', {}).get('content_category', 'general'),
                "tags": note.get('metadata', {}).get('tags', []),
                "word_count": len(note.get('content', '').split()),
                "intent": note.get('intent', 'learn'),
                "user_note": note.get('user_note', ''),
                "raw_note": note
            }
            display_notes.append(display_note)
        
        return NotesResponse(
            notes=display_notes,
            pagination=PaginationInfo(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total
            ),
            stats={
                "total_notes": total,
                "returned": len(display_notes),
                "memory_usage": "display_optimized"
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Error retrieving notes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving notes: {str(e)}")


@router.get("/batches")
async def get_batches():
    """Get batch processing history"""
    try:
        return {
            "batches": batches_storage,
            "total_batches": len(batches_storage),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving batches: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batches: {str(e)}")


@router.get("/results")
async def get_results(
    bake_id: Optional[str] = Query(None, description="Specific bake ID to retrieve")
):
    """Get processing results"""
    try:
        if bake_id:
            # Look for specific bake result
            for result in processing_results:
                if result.get('bake_id') == bake_id:
                    formatted_result = {
                        'bake_id': bake_id,
                        'status': result.get('status', 'unknown'),
                        'found': True,
                        'source': 'memory',
                        
                        'key_metrics': {
                            'captures_processed': result.get('processing_summary', {}).get('captures_processed', 0),
                            'concepts_extracted': result.get('processing_summary', {}).get('concepts_extracted', 0),
                            'api_calls_saved': result.get('batch_optimization', {}).get('api_calls_saved', 0),
                            'processing_time_seconds': result.get('processing_summary', {}).get('processing_time_seconds', 0),
                            'session_theme': result.get('processing_summary', {}).get('session_theme', 'general')
                        },
                        
                        'result': result,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    return formatted_result
            
            raise HTTPException(
                status_code=404,
                detail=f"No results found for bake_id: {bake_id}"
            )
        
        else:
            total_captures = sum(r.get('processing_summary', {}).get('captures_processed', 0) for r in processing_results)
            total_api_calls_saved = sum(r.get('batch_optimization', {}).get('api_calls_saved', 0) for r in processing_results)
            
            return {
                "results": processing_results,
                "summary": {
                    "total_results": len(processing_results),
                    "total_captures_processed": total_captures,
                    "total_api_calls_saved": total_api_calls_saved,
                    "successful_bakes": len([r for r in processing_results if r.get('status') == 'completed'])
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")


@router.delete("/notes")
async def clear_notes():
    """Clear all stored notes (for testing)"""
    try:
        global notes_storage
        notes_storage = []
        logger.info("All notes cleared")
        return {
            "status": "success", 
            "message": "All notes cleared",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing notes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing notes: {str(e)}")


@router.post("/cleanup")
async def cleanup_data():
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
        
        return {
            "success": True,
            "message": "Cleanup completed",
            "stats": {
                "processed_batches": len(processed_batches),
                "processed_bakes": len(processed_bakes),
                "content_hashes": len(content_hashes)
            }
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/files")
async def get_notes_files_info():
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
        
        return {
            "file_count": len(file_info),
            "files": file_info,
            "total_size_bytes": sum(f["size_bytes"] for f in file_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting file info: {str(e)}")


# Background processing functions

async def process_batch_background(batch_id: str, notes):
    """Background processing of a batch of notes"""
    logger.info(f"Processing batch {batch_id} in background")
    
    try:
        import asyncio
        # Simulate processing time
        await asyncio.sleep(2)
        
        processed_notes = []
        for note in notes:
            processed_note = {
                "original": note,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processing_status": "completed",
                "insights": f"Processed note from {note.get('source', {}).get('url', note.get('source_url', 'unknown'))}",
                "categories": [note.get('metadata', {}).get('content_category', note.get('intent', 'general'))],
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


async def process_bake_background(bake_data):
    """Background processing of bake request"""
    from pipeline_orchestrator import PipelineOrchestrator
    
    bake_id = bake_data['bake_id']
    
    print(f"\n🎬 === BACKGROUND THREAD EXECUTING for {bake_id} ===")
    print(f"📊 Notes in storage: {len(notes_storage)}")
    
    logger.info(f"Processing bake {bake_id} in background")
    
    try:
        # Initialize pipeline orchestrator
        try:
            pipeline_orchestrator = PipelineOrchestrator()
            logger.info("Pipeline orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline orchestrator: {str(e)}")
            pipeline_orchestrator = None
        
        if not pipeline_orchestrator:
            raise Exception("Pipeline orchestrator not available")
        
        session_notes = notes_storage.copy()
        print(f"📋 Running pipeline on {len(session_notes)} notes for bake {bake_id}")
        
        try:
            pipeline_results = pipeline_orchestrator.run_pipeline(session_notes, bake_data)
            print(f"✅ PIPELINE COMPLETED. Result keys: {list(pipeline_results.keys())}")
        except Exception as pipeline_error:
            logger.error(f"Pipeline execution failed for {bake_id}: {str(pipeline_error)}")
            raise pipeline_error
        
        try:
            api_response = {
                'bake_id': bake_id,
                'status': pipeline_results.get('status', 'completed'),
                'processed_at': pipeline_results.get('processed_at', datetime.now(timezone.utc).isoformat()),
                'input_notes_count': len(session_notes),
                
                'batch_optimization': pipeline_results.get('batch_optimization', {}),
                
                'processing_summary': {
                    'captures_processed': pipeline_results.get('summary', {}).get('captures_processed', len(session_notes)),
                    'concepts_extracted': pipeline_results.get('summary', {}).get('concepts_extracted', 0),
                    'api_calls_saved': pipeline_results.get('batch_optimization', {}).get('api_calls_saved', 0),
                    'processing_time_seconds': pipeline_results.get('processing_time', 0),
                    'session_theme': pipeline_results.get('learning_analysis', {}).get('session_theme', 'general')
                },
                
                'insights': pipeline_results.get('learning_analysis', {}),
                'knowledge_insights': pipeline_results.get('knowledge_insights', {}),
                'outputs': pipeline_results.get('outputs', {}),
                
                'detailed_results': pipeline_results,
                
                'pipeline_metadata': {
                    'pipeline_version': pipeline_results.get('metadata', {}).get('pipeline_version', '1.1.0'),
                    'nodes_executed': pipeline_results.get('metadata', {}).get('nodes_executed', 0),
                    'input_format': 'minimal_capture'
                }
            }
        except Exception as format_error:
            logger.error(f"Result formatting failed for {bake_id}: {str(format_error)}")
            api_response = {
                'bake_id': bake_id,
                'status': 'completed_with_formatting_issues',
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'input_notes_count': len(session_notes),
                'batch_optimization': {},
                'processing_summary': {
                    'captures_processed': len(session_notes),
                    'concepts_extracted': 0,
                    'api_calls_saved': 0,
                    'processing_time_seconds': 0,
                    'session_theme': 'general'
                },
                'error': f'Formatting error: {str(format_error)}',
                'raw_pipeline_results': pipeline_results
            }
        
        processing_results.append(api_response)
        print(f"✅ FORMATTED RESULT ADDED TO MEMORY for bake {bake_id}")
        
        batch_metrics = api_response.get('batch_optimization', {})
        api_calls_saved = batch_metrics.get('api_calls_saved', 0)

        if api_calls_saved > 0:
            print(f"🎉 BATCH OPTIMIZATION SUCCESS: {api_calls_saved} API calls saved!")
            logger.info(f"Batch optimization successful: {api_calls_saved} API calls saved")
        else:
            print(f"⚠️  No batch optimization detected (this might be expected for small batches)")
            logger.info(f"No batch optimization detected for bake {bake_id}")

        try:
            result_file = RESULTS_DIR / f"bake_{bake_id}_pipeline_result.json"
            with open(result_file, 'w') as f:
                json.dump(api_response, f, indent=2, default=str)
            logger.info(f"Results saved to file: {result_file}")
        except Exception as save_error:
            logger.warning(f"Failed to save results to file: {str(save_error)}")
        
        logger.info(f"Pipeline bake {bake_id} completed successfully")
        print(f"✅ BACKGROUND PROCESSING COMPLETE for {bake_id}")
                
    except Exception as e:
        print(f"❌ ERROR in background processing for {bake_id}: {str(e)}")
        logger.error(f"Error processing bake {bake_id}: {str(e)}")
        logger.error(traceback.format_exc())
                
        error_result = {
            "bake_id": bake_id,
            "status": "failed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "input_notes_count": len(notes_storage) if notes_storage else 0,
            "error": str(e),
            "error_type": type(e).__name__,
            "error_context": {
                "pipeline_orchestrator_available": False,
                "notes_storage_count": len(notes_storage) if notes_storage else 0,
                "bake_data_keys": list(bake_data.keys()) if bake_data else []
            },
            "batch_optimization": {},
            "processing_summary": {
                "captures_processed": 0,
                "concepts_extracted": 0,
                "api_calls_saved": 0,
                "processing_time_seconds": 0,
                "session_theme": "error"
            }
        }

        processing_results.append(error_result)
        print(f"❌ ERROR RESULT ADDED TO MEMORY for bake {bake_id}")

        try:
            error_file = RESULTS_DIR / f"bake_{bake_id}_error.json"
            with open(error_file, 'w') as f:
                json.dump(error_result, f, indent=2, default=str)
        except Exception:
            pass


async def save_individual_notes_background(notes, batch_id: str):
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