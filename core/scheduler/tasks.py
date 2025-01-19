from apscheduler.schedulers.background import BackgroundScheduler
from config.settings import (
    SECURITY_CHECK_INTERVAL,
    SSH_CLEANUP_INTERVAL,
    LONG_RUNNING_CLEANUP_INTERVAL,
    SSH_SESSION_TIMEOUT
)

def init_scheduler(security_checker, ssh_manager):
    """
    Initialize and configure the background scheduler with all required jobs.
    
    Args:
        security_checker: SecurityChecker instance
        ssh_manager: SSHManager instance
    
    Returns:
        BackgroundScheduler: Configured scheduler instance
    """
    scheduler = BackgroundScheduler()

    # Add Security Analysis job
    scheduler.add_job(
        security_checker.fetch_and_analyze, 
        'interval', 
        seconds=SECURITY_CHECK_INTERVAL,
        max_instances=2,
        id='security_analysis'
    )
    
    # Add SSH cleanup jobs
    scheduler.add_job(
        lambda: ssh_manager.cleanup_long_running_sessions(
            max_session_time=SSH_SESSION_TIMEOUT
        ),
        'interval',
        seconds=LONG_RUNNING_CLEANUP_INTERVAL,
        id='long_running_cleanup'
    )

    # Use lambda to pass ssh_manager to cleanup_ssh_sessions
    scheduler.add_job(
        lambda: cleanup_ssh_sessions(ssh_manager),
        'interval',
        seconds=SSH_CLEANUP_INTERVAL,
        id='ssh_cleanup'
    )
    
    scheduler.start()
    return scheduler

def cleanup_ssh_sessions(ssh_manager):
    """
    Cleanup inactive SSH sessions.
    
    Args:
        ssh_manager: SSHManager instance
    """
    ssh_manager.cleanup_inactive_sessions()