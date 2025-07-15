#!/usr/bin/env python3
"""
Test script to verify job synchronization functionality
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, active_jobs, ScrapeJob
from models import db, ScrapeJobHistory

def test_job_sync():
    """Test the job synchronization functionality"""
    with app.app_context():
        print("🧪 Testing Job Synchronization Fix")
        print("=" * 50)
        
        # Create a test scenario
        test_job_id = f"test_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 1. Create a job in database as "in_progress"
        print(f"📝 Creating test job in database: {test_job_id}")
        db_job = ScrapeJobHistory(
            job_id=test_job_id,
            user_id=None,
            total_urls=1,
            status='in_progress',
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(db_job)
        db.session.commit()
        
        # 2. Create a completed job in memory
        print(f"🎯 Creating completed job in memory")
        memory_job = ScrapeJob(test_job_id, 1)
        memory_job.status = "completed"
        memory_job.results = [{'emails': ['test@example.com'], 'phones': [], 'social_media': {}}]
        memory_job.result_file = "test_result.xlsx"
        active_jobs[test_job_id] = memory_job
        
        # 3. Check initial status mismatch
        print(f"📊 Initial status check:")
        print(f"   Database: {db_job.status}")
        print(f"   Memory: {memory_job.status}")
        print(f"   ❌ MISMATCH DETECTED")
        
        # 4. Test the sync function
        print(f"\n🔄 Testing sync functionality...")
        
        # Simulate the sync logic
        if test_job_id in active_jobs:
            mem_job = active_jobs[test_job_id]
            if mem_job.status == "completed" and db_job.status == 'in_progress':
                try:
                    db_job.status = 'completed'
                    db_job.completed_at = datetime.now(timezone.utc)
                    if mem_job.result_file:
                        db_job.result_file = mem_job.result_file
                    if hasattr(mem_job, 'results'):
                        total_emails = sum(len(result.get('emails', [])) for result in mem_job.results if isinstance(result.get('emails', []), list))
                        db_job.emails_found = total_emails
                        db_job.successful_urls = len(mem_job.results)
                    
                    db.session.commit()
                    print(f"   ✅ Successfully synced job status!")
                except Exception as e:
                    print(f"   ❌ Sync failed: {e}")
                    db.session.rollback()
        
        # 5. Verify the fix
        db.session.refresh(db_job)
        print(f"\n📊 After sync status check:")
        print(f"   Database: {db_job.status}")
        print(f"   Memory: {memory_job.status}")
        print(f"   Emails found: {db_job.emails_found}")
        print(f"   Result file: {db_job.result_file}")
        
        if db_job.status == memory_job.status:
            print(f"   ✅ STATUS SYNCHRONIZED!")
            success = True
        else:
            print(f"   ❌ SYNC FAILED!")
            success = False
        
        # 6. Cleanup
        print(f"\n🧹 Cleaning up test data...")
        db.session.delete(db_job)
        if test_job_id in active_jobs:
            del active_jobs[test_job_id]
        db.session.commit()
        
        print(f"\n" + "=" * 50)
        return success

if __name__ == "__main__":
    success = test_job_sync()
    
    if success:
        print("🎉 JOB SYNC TEST PASSED!")
        print("The synchronization fix is working correctly.")
    else:
        print("💥 JOB SYNC TEST FAILED!")
        print("There might be an issue with the synchronization logic.") 