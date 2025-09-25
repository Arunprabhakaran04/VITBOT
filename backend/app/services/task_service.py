from ...database_connection import get_db_connection
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from ...celery_app import celery_app
from ...redis_cache import cache


class TaskService:
    """Service for managing user task tracking"""
    
    @staticmethod
    def store_user_task(user_id: int, task_id: str, task_type: str, filename: str = None) -> bool:
        """Store a new task for a user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            
            cursor.execute("""
                INSERT INTO user_tasks (user_id, task_id, task_type, filename, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, task_id, task_type, filename, 'queued', now, now))
            
            conn.commit()
            return True
    
    @staticmethod
    def get_user_active_tasks(user_id: int) -> List[Dict]:
        """Get all active tasks for a user with caching"""
        cache_key = f"active_tasks:user:{user_id}"
        
        # Try cache first (cache for 30 seconds to reduce DB load)
        cached_tasks = cache.get_json(cache_key)
        if cached_tasks:
            return cached_tasks
        
        # Get from database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT task_id, task_type, status, filename, created_at, updated_at, progress_message
                FROM user_tasks
                WHERE user_id = %s AND status IN ('queued', 'processing')
                ORDER BY created_at DESC
            """, (user_id,))
            
            tasks = cursor.fetchall()
            task_list = [dict(task) for task in tasks]
            
            # Cache the result
            cache.set_json(cache_key, task_list, expire=30)
            
            return task_list
    
    @staticmethod
    def get_user_completed_tasks(user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent completed tasks for a user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT task_id, task_type, status, filename, created_at, updated_at, progress_message
                FROM user_tasks
                WHERE user_id = %s AND status IN ('completed', 'failed')
                ORDER BY updated_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            tasks = cursor.fetchall()
            return [dict(task) for task in tasks]
    
    @staticmethod
    def update_task_status(task_id: str, status: str, progress_message: str = None) -> bool:
        """Update task status and progress, invalidate cache"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            
            cursor.execute("""
                UPDATE user_tasks
                SET status = %s, updated_at = %s, progress_message = %s
                WHERE task_id = %s
            """, (status, now, progress_message, task_id))
            
            conn.commit()
            
            # Invalidate related caches
            if cursor.rowcount > 0:
                # Get user_id to clear user-specific cache
                cursor.execute("SELECT user_id FROM user_tasks WHERE task_id = %s", (task_id,))
                result = cursor.fetchone()
                if result:
                    user_id = result['user_id']  # Use dictionary key instead of index
                    cache.delete(f"active_tasks:user:{user_id}")
            
            return cursor.rowcount > 0
    
    @staticmethod
    def get_task_with_celery_status(task_id: str) -> Optional[Dict]:
        """Get task from database with live Celery status"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, task_id, task_type, status, filename, created_at, updated_at, progress_message
                FROM user_tasks
                WHERE task_id = %s
            """, (task_id,))
            
            task = cursor.fetchone()
            if not task:
                return None
            
            task_dict = dict(task)
            
            # Get live status from Celery
            try:
                celery_task = celery_app.AsyncResult(task_id)
                
                if celery_task.state == 'PENDING':
                    live_status = 'queued'
                    live_message = 'Task is waiting to be processed'
                elif celery_task.state == 'PROCESSING':
                    live_status = 'processing'
                    live_message = celery_task.info.get('message', 'Processing...')
                elif celery_task.state == 'SUCCESS':
                    live_status = 'completed'
                    live_message = 'Task completed successfully'
                elif celery_task.state == 'FAILURE':
                    live_status = 'failed'
                    live_message = str(celery_task.info) if celery_task.info else 'Task failed'
                else:
                    live_status = task_dict['status']
                    live_message = task_dict['progress_message']
                
                # Update database if status changed
                if live_status != task_dict['status']:
                    TaskService.update_task_status(task_id, live_status, live_message)
                
                task_dict['status'] = live_status
                task_dict['progress_message'] = live_message
                
            except Exception as e:
                print(f"Error getting Celery status for task {task_id}: {e}")
            
            return task_dict
    
    @staticmethod
    def cleanup_old_tasks(days_old: int = 30) -> int:
        """Clean up old completed/failed tasks"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            cursor.execute("""
                DELETE FROM user_tasks
                WHERE status IN ('completed', 'failed') AND updated_at < %s
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    @staticmethod
    def get_user_tasks_summary(user_id: int) -> Dict:
        """Get summary of user tasks"""
        active_tasks = TaskService.get_user_active_tasks(user_id)
        completed_tasks = TaskService.get_user_completed_tasks(user_id)
        
        # Update active tasks with live Celery status
        updated_active_tasks = []
        for task in active_tasks:
            updated_task = TaskService.get_task_with_celery_status(task['task_id'])
            if updated_task:
                updated_active_tasks.append(updated_task)
        
        return {
            'user_id': user_id,
            'active_tasks': updated_active_tasks,
            'completed_tasks': completed_tasks,
            'total_active': len(updated_active_tasks),
            'total_completed': len(completed_tasks)
        } 