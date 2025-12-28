"""
任务调度器
"""
import asyncio
from datetime import datetime
from typing import Optional, Callable, Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..config import get_config, SchedulerConfig


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._task_history: List[dict] = []
        self._max_history = 100
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
    
    def add_cron_job(self, 
                     job_id: str, 
                     func: Callable, 
                     cron_expr: str,
                     replace_existing: bool = True) -> bool:
        """添加定时任务
        
        Args:
            job_id: 任务ID
            func: 任务函数
            cron_expr: Cron表达式 (格式: 分 时 日 月 星期)
            replace_existing: 是否替换已存在的任务
            
        Returns:
            是否成功
        """
        try:
            # 解析Cron表达式
            parts = cron_expr.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
            else:
                raise ValueError(f"Invalid cron expression: {cron_expr}")
            
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                replace_existing=replace_existing
            )
            
            self._log_task(job_id, "added", f"Cron: {cron_expr}")
            return True
            
        except Exception as e:
            self._log_task(job_id, "error", str(e))
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        try:
            self.scheduler.remove_job(job_id)
            self._log_task(job_id, "removed", "")
            return True
        except Exception:
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            self._log_task(job_id, "paused", "")
            return True
        except Exception:
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            self._log_task(job_id, "resumed", "")
            return True
        except Exception:
            return False
    
    def get_jobs(self) -> List[dict]:
        """获取所有任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "pending": job.pending
            })
        return jobs
    
    def get_history(self, limit: int = 20) -> List[dict]:
        """获取任务历史"""
        return self._task_history[-limit:]
    
    def _log_task(self, job_id: str, action: str, detail: str):
        """记录任务日志"""
        self._task_history.append({
            "job_id": job_id,
            "action": action,
            "detail": detail,
            "timestamp": datetime.now().isoformat()
        })
        
        # 限制历史记录数量
        if len(self._task_history) > self._max_history:
            self._task_history = self._task_history[-self._max_history:]


# 全局调度器实例
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
