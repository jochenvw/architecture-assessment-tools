"""Resume semantics: succeeded work is never repeated; expired leases resume."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _harness import Pipeline
from foundry_estate_assessment.scheduler import Scheduler, TaskSpec
from foundry_estate_assessment.models import TaskStatus


class ResumeTest(unittest.TestCase):
    def test_succeeded_tasks_not_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                tasks = pipe.db.list_tasks(pipe.assessment_id, pipe.snapshot_id)
                self.assertTrue(tasks)
                self.assertTrue(all(t["status"] == TaskStatus.SUCCEEDED.value for t in tasks))

                # Re-run the same specs: no executor should be invoked because
                # every task already SUCCEEDED and refresh is False.
                calls: list[str] = []
                specs = [TaskSpec(t["resource_id"], t["collector"]) for t in tasks]
                executors = {
                    t["collector"]: (lambda rid, c=t["collector"]: calls.append(c))
                    for t in tasks
                }
                sched = Scheduler(pipe.db, pipe.assessment_id, pipe.snapshot_id, refresh=False)
                sched.run(specs, executors)
                self.assertEqual(calls, [])
            finally:
                pipe.close()

    def test_expired_lease_is_reclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp))
            try:
                pipe.inventory()
                specs = pipe_specs = [TaskSpec(r["resource_id"], "foundry")
                                      for r in pipe.db.list_resources(pipe.snapshot_id, classifications=["foundry-current"])]
                sched = Scheduler(pipe.db, pipe.assessment_id, pipe.snapshot_id)
                sched.ensure_tasks(specs)
                task_id = specs[0].task_id
                # Simulate a crashed worker: RUNNING with a lease in the past.
                pipe.db.set_task_status(task_id, status="RUNNING", lease_expiry="2000-01-01T00:00:00Z")
                sched.reclaim_expired_leases()
                row = pipe.db.get_task(task_id)
                self.assertEqual(row["status"], "PENDING")
                # And it is therefore runnable again.
                self.assertTrue(sched._is_runnable(row))
            finally:
                pipe.close()

    def test_blocked_tasks_preserved_unless_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp))
            try:
                pipe.inventory()
                spec = TaskSpec(
                    pipe.db.list_resources(pipe.snapshot_id, classifications=["foundry-current"])[0]["resource_id"],
                    "foundry",
                )
                sched = Scheduler(pipe.db, pipe.assessment_id, pipe.snapshot_id, retry_blocked=False)
                sched.ensure_tasks([spec])
                pipe.db.set_task_status(spec.task_id, status="BLOCKED_PERMISSION")
                row = pipe.db.get_task(spec.task_id)
                self.assertFalse(sched._is_runnable(row))
                sched_retry = Scheduler(pipe.db, pipe.assessment_id, pipe.snapshot_id, retry_blocked=True)
                self.assertTrue(sched_retry._is_runnable(row))
            finally:
                pipe.close()


if __name__ == "__main__":
    unittest.main()
