"""
Data Retention CLI Commands

Command-line interface for running data retention cleanup tasks.
These commands can be scheduled with cron for automatic execution.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import click
from sqlalchemy.orm import Session

from app.core.database import get_database_session
from app.services.data_retention_service import get_data_retention_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def data_retention():
    """Data retention management commands."""
    pass


@data_retention.command()
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
@click.option('--inactive-days', type=int, help='Days of inactivity before account deletion')
@click.option('--max-deletions', type=int, default=100, help='Maximum accounts to delete in one run')
def cleanup_inactive_accounts(dry_run: bool, inactive_days: Optional[int], max_deletions: int):
    """Clean up inactive user accounts."""
    click.echo(f"Starting inactive account cleanup {'(DRY RUN)' if dry_run else ''}...")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Run cleanup
        result = asyncio.run(retention_service.cleanup_inactive_accounts(
            inactive_days=inactive_days,
            dry_run=dry_run,
            max_deletions=max_deletions
        ))
        
        # Display results
        click.echo(f"Results:")
        click.echo(f"  Total inactive accounts found: {result['total_inactive_found']}")
        click.echo(f"  Accounts processed: {result['accounts_to_delete']}")
        click.echo(f"  Accounts deleted: {result['accounts_deleted']}")
        click.echo(f"  Deletions failed: {result['deletions_failed']}")
        click.echo(f"  Inactive threshold: {result['inactive_threshold_days']} days")
        
        if dry_run:
            click.echo("\nThis was a dry run. No accounts were actually deleted.")
        
        # Optionally save detailed results to file
        if click.confirm('Save detailed results to file?'):
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"account_cleanup_results_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"Results saved to {filename}")
        
    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        raise click.ClickException(f"Cleanup failed: {e}")
    finally:
        db_session.close()


@data_retention.command()
@click.option('--dry-run', is_flag=True, help='Show what warnings would be sent without sending them')
@click.option('--warning-days', type=int, help='Days of inactivity before sending warning')
def send_warnings(dry_run: bool, warning_days: Optional[int]):
    """Send inactivity warnings to users."""
    click.echo(f"Starting inactivity warning process {'(DRY RUN)' if dry_run else ''}...")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Send warnings
        result = asyncio.run(retention_service.send_inactivity_warnings(
            dry_run=dry_run
        ))
        
        # Display results
        click.echo(f"Results:")
        click.echo(f"  Total accounts found: {result['total_accounts']}")
        click.echo(f"  Warnings sent: {result['warnings_sent']}")
        click.echo(f"  Warnings failed: {result['warnings_failed']}")
        
        if dry_run:
            click.echo("\nThis was a dry run. No warnings were actually sent.")
        
        # Show some details
        if result['results']:
            click.echo("\nSample results:")
            for i, res in enumerate(result['results'][:5]):  # Show first 5
                click.echo(f"  {i+1}. {res['email']} - {res['status']} ({res.get('inactive_days', 'N/A')} days inactive)")
            
            if len(result['results']) > 5:
                click.echo(f"  ... and {len(result['results']) - 5} more")
        
    except Exception as e:
        click.echo(f"Error sending warnings: {e}", err=True)
        raise click.ClickException(f"Warning process failed: {e}")
    finally:
        db_session.close()


@data_retention.command()
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without actually cleaning')
@click.option('--expired-days', type=int, help='Days after expiration to clean up sessions')
def cleanup_sessions(dry_run: bool, expired_days: Optional[int]):
    """Clean up expired authentication sessions."""
    click.echo(f"Starting session cleanup {'(DRY RUN)' if dry_run else ''}...")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Clean up sessions
        result = retention_service.cleanup_expired_sessions(
            expired_days=expired_days,
            dry_run=dry_run
        )
        
        # Display results
        click.echo(f"Results:")
        click.echo(f"  Expired sessions found: {result['expired_sessions_found']}")
        click.echo(f"  Sessions deleted: {result['sessions_deleted']}")
        click.echo(f"  Cutoff date: {result['cutoff_date']}")
        
        if dry_run:
            click.echo("\nThis was a dry run. No sessions were actually deleted.")
        
    except Exception as e:
        click.echo(f"Error during session cleanup: {e}", err=True)
        raise click.ClickException(f"Session cleanup failed: {e}")
    finally:
        db_session.close()


@data_retention.command()
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without actually cleaning')
@click.option('--retention-days', type=int, help='Days to retain audit logs')
def cleanup_audit_logs(dry_run: bool, retention_days: Optional[int]):
    """Clean up old audit logs."""
    click.echo(f"Starting audit log cleanup {'(DRY RUN)' if dry_run else ''}...")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Clean up audit logs
        result = retention_service.cleanup_old_audit_logs(
            retention_days=retention_days,
            dry_run=dry_run
        )
        
        # Display results
        click.echo(f"Results:")
        click.echo(f"  Old logs found: {result['old_logs_found']}")
        click.echo(f"  Logs deleted: {result['logs_deleted']}")
        click.echo(f"  Retention period: {result['retention_days']} days")
        click.echo(f"  Cutoff date: {result['cutoff_date']}")
        
        if dry_run:
            click.echo("\nThis was a dry run. No logs were actually deleted.")
        
    except Exception as e:
        click.echo(f"Error during audit log cleanup: {e}", err=True)
        raise click.ClickException(f"Audit log cleanup failed: {e}")
    finally:
        db_session.close()


@data_retention.command()
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without actually cleaning')
def full_cleanup(dry_run: bool):
    """Run comprehensive data retention cleanup."""
    click.echo(f"Starting full data retention cleanup {'(DRY RUN)' if dry_run else ''}...")
    click.echo("This will run all cleanup tasks in sequence.\n")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Run full cleanup
        result = asyncio.run(retention_service.run_full_retention_cleanup(
            dry_run=dry_run
        ))
        
        # Display results
        click.echo(f"Full cleanup completed!")
        click.echo(f"  Started: {result['started_at']}")
        click.echo(f"  Completed: {result['completed_at']}")
        click.echo(f"  Success: {result['success']}")
        
        if 'error' in result:
            click.echo(f"  Error: {result['error']}", err=True)
        
        # Show task results
        for task_name, task_result in result['cleanup_tasks'].items():
            click.echo(f"\n{task_name.replace('_', ' ').title()}:")
            
            if task_name == 'inactivity_warnings':
                click.echo(f"  Warnings sent: {task_result['warnings_sent']}")
                click.echo(f"  Warnings failed: {task_result['warnings_failed']}")
            
            elif task_name == 'inactive_accounts':
                click.echo(f"  Accounts deleted: {task_result['accounts_deleted']}")
                click.echo(f"  Deletions failed: {task_result['deletions_failed']}")
            
            elif task_name == 'expired_sessions':
                click.echo(f"  Sessions deleted: {task_result['sessions_deleted']}")
            
            elif task_name == 'old_audit_logs':
                click.echo(f"  Logs deleted: {task_result['logs_deleted']}")
        
        if dry_run:
            click.echo("\nThis was a dry run. No data was actually deleted.")
        
        # Save results to file
        if not dry_run and click.confirm('Save detailed results to file?'):
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"full_cleanup_results_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            click.echo(f"Results saved to {filename}")
        
    except Exception as e:
        click.echo(f"Error during full cleanup: {e}", err=True)
        raise click.ClickException(f"Full cleanup failed: {e}")
    finally:
        db_session.close()


@data_retention.command()
def statistics():
    """Show data retention statistics."""
    click.echo("Generating data retention statistics...")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Get statistics
        stats = retention_service.get_retention_statistics()
        
        # Display statistics
        click.echo(f"\nData Retention Statistics")
        click.echo(f"Generated: {stats['generated_at']}\n")
        
        # User statistics
        user_stats = stats['user_statistics']
        click.echo("User Statistics:")
        click.echo(f"  Total active users: {user_stats['total_active_users']}")
        click.echo(f"  Inactive for 22+ months (warning eligible): {user_stats['eligible_for_warning']}")
        click.echo(f"  Inactive for 24+ months (deletion eligible): {user_stats['eligible_for_deletion']}")
        
        # Session statistics
        session_stats = stats['session_statistics']
        click.echo(f"\nSession Statistics:")
        click.echo(f"  Total sessions: {session_stats['total_sessions']}")
        click.echo(f"  Expired sessions (cleanup eligible): {session_stats['expired_sessions_eligible_for_cleanup']}")
        
        # Audit statistics
        audit_stats = stats['audit_statistics']
        click.echo(f"\nAudit Log Statistics:")
        click.echo(f"  Total audit logs: {audit_stats['total_audit_logs']}")
        click.echo(f"  Old logs (cleanup eligible): {audit_stats['old_logs_eligible_for_cleanup']}")
        
    except Exception as e:
        click.echo(f"Error generating statistics: {e}", err=True)
        raise click.ClickException(f"Statistics generation failed: {e}")
    finally:
        db_session.close()


@data_retention.command()
@click.option('--inactive-days', type=int, default=730, help='Days of inactivity to check')
@click.option('--limit', type=int, default=10, help='Maximum accounts to show')
def list_inactive(inactive_days: int, limit: int):
    """List inactive accounts."""
    click.echo(f"Finding accounts inactive for {inactive_days}+ days...")
    
    try:
        # Get database session
        db_session = next(get_database_session())
        retention_service = get_data_retention_service(db_session)
        
        # Find inactive accounts
        inactive_accounts = retention_service.find_inactive_accounts(inactive_days)
        
        if not inactive_accounts:
            click.echo("No inactive accounts found.")
            return
        
        # Display results
        click.echo(f"\nFound {len(inactive_accounts)} inactive accounts:")
        click.echo("(Showing first {} accounts)\n".format(min(limit, len(inactive_accounts))))
        
        for i, account in enumerate(inactive_accounts[:limit]):
            click.echo(f"{i+1}. {account['email']}")
            click.echo(f"   User ID: {account['user_id']}")
            click.echo(f"   Inactive days: {account['inactive_days']}")
            click.echo(f"   Last activity: {account['last_activity']}")
            click.echo(f"   Account age: {account['account_age_days']} days")
            click.echo()
        
        if len(inactive_accounts) > limit:
            click.echo(f"... and {len(inactive_accounts) - limit} more accounts")
        
    except Exception as e:
        click.echo(f"Error listing inactive accounts: {e}", err=True)
        raise click.ClickException(f"Failed to list inactive accounts: {e}")
    finally:
        db_session.close()


if __name__ == '__main__':
    data_retention()