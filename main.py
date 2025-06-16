"""
Main Pipeline Entry Point
Orchestrates the AI Note Generation Pipeline for Web Research → Obsidian Notes
"""

from pocketflow import PipelineRunner
from nodes.capture_ingestion import CaptureIngestionNode
