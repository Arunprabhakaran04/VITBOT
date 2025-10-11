"""
Background Task Service - In-process task queue replacement for Celery
Handles PDF processing and other background tasks using threading
"""
import asyncio
import logging
import threading
import time
import uuid
from queue import Queue, Empty
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from enum import Enum
from loguru import logger

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    task_type: str
    data: Dict[str, Any]
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    progress: int = 0
    message: str = ""

class BackgroundTaskService:
    def __init__(self, max_workers: int = 2):
        self.task_queue = Queue()
        self.tasks: Dict[str, Task] = {}
        self.workers = []
        self.max_workers = max_workers
        self.running = False
        self.handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type"""
        self.handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    def start(self):
        """Start the background workers"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.max_workers} background workers")
    
    def stop(self):
        """Stop all background workers"""
        self.running = False
        # Send stop signals to all workers
        for _ in range(self.max_workers):
            self.task_queue.put(None)  # Sentinel to stop workers
        
        logger.info("Stopping background workers...")
    
    def add_task(self, task_type: str, data: Dict[str, Any]) -> str:
        """Add a new task to the queue"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            task_type=task_type,
            data=data,
            status=TaskStatus.PENDING,
            created_at=time.time(),
            message="Task queued"
        )
        
        with self._lock:
            self.tasks[task_id] = task
        
        self.task_queue.put(task)
        
        logger.info(f"Added task {task_id} of type {task_type}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get the status of a specific task"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.task_queue.qsize()
    
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active tasks"""
        with self._lock:
            active_tasks = {}
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                    active_tasks[task_id] = {
                        "id": task.id,
                        "type": task.task_type,
                        "status": task.status.value,
                        "progress": task.progress,
                        "message": task.message,
                        "created_at": task.created_at,
                        "started_at": task.started_at
                    }
            return active_tasks
    
    def update_task_progress(self, task_id: str, progress: int, message: str = ""):
        """Update task progress"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].progress = progress
                if message:
                    self.tasks[task_id].message = message
    
    def _worker(self, worker_id: int):
        """Worker thread function"""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:  # Sentinel to stop
                    break
                
                self._process_task(task, worker_id)
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _process_task(self, task: Task, worker_id: int):
        """Process a single task"""
        try:
            # Update task status
            with self._lock:
                task.status = TaskStatus.PROCESSING
                task.started_at = time.time()
                task.message = "Processing started"
            
            logger.info(f"Worker {worker_id} processing task {task.id} of type {task.task_type}")
            
            if task.task_type not in self.handlers:
                raise ValueError(f"No handler for task type: {task.task_type}")
            
            handler = self.handlers[task.task_type]
            
            # Create a mock Celery-like task object for compatibility
            class MockCeleryTask:
                def __init__(self, task_obj):
                    self.task_obj = task_obj
                    self.request = type('obj', (object,), {'id': task_obj.id})()
                
                def update_state(self, state=None, meta=None):
                    if meta and 'message' in meta:
                        self.task_obj.message = meta['message']
            
            mock_task = MockCeleryTask(task)
            
            # Execute the handler
            result = handler(mock_task, **task.data)
            
            # Update task completion
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.progress = 100
                task.message = "Task completed successfully"
            
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            # Update task failure
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = time.time()
                task.message = f"Task failed: {str(e)}"
            
            logger.error(f"Task {task.id} failed: {e}")

# Global instance
background_service = BackgroundTaskService(max_workers=2)