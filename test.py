import unittest
import json
from scheduler import select_best_node, run_scheduling_cycle, JOBS_FILE, NODES_FILE

class TestNodeSelection(unittest.TestCase):

    def test_high_priority_job_selects_on_demand(self):
        """
        Test case: A high-priority job correctly selects a more expensive
        on-demand node when no suitable spot instances are available.
        """
        job = {
            "jobId": "job-high-prio",
            "priority": 10,
            "resourceRequest": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0},
            "slaType": "BATCH",
            "maxTolerableCost": 2.0,
            "isRescheduled": False
        }
        nodes = [
            # A spot node that is too small
            {"nodeId": "node-spot-small", "cloudProvider": "AWS", "instanceType": "c5.large", "totalCapacity": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "nodeType": "SPOT", "realTimeCostPerMinute": 0.5},
            # A suitable on-demand node
            {"nodeId": "node-on-demand-large", "cloudProvider": "AWS", "instanceType": "c5.xlarge", "totalCapacity": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 1.5}
        ]
        
        best_node = select_best_node(job, nodes)
        self.assertIsNotNone(best_node)
        self.assertEqual(best_node['nodeId'], "node-on-demand-large")

    def test_low_priority_job_waits_if_too_expensive(self):
        """
        Test case: A low-priority, cost-sensitive job correctly returns None
        if the only available nodes are too expensive.
        """
        job = {
            "jobId": "job-low-prio-cost",
            "priority": 2,
            "resourceRequest": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0},
            "slaType": "BATCH",
            "maxTolerableCost": 0.5,
            "isRescheduled": False
        }
        nodes = [
            # A node that fits the resources but is too expensive
            {"nodeId": "node-expensive", "cloudProvider": "AWS", "instanceType": "c5.large", "totalCapacity": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 0.8}
        ]
        
        best_node = select_best_node(job, nodes)
        self.assertIsNone(best_node)

    def test_cheaper_spot_node_is_selected(self):
        """
        Test case: Given two identical spot nodes, the cheaper one is selected.
        """
        job = {
            "jobId": "job-spot",
            "priority": 5,
            "resourceRequest": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0},
            "slaType": "BATCH",
            "maxTolerableCost": 1.0,
            "isRescheduled": False
        }
        nodes = [
            {"nodeId": "node-spot-cheaper", "cloudProvider": "AWS", "instanceType": "m5.large", "totalCapacity": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "nodeType": "SPOT", "realTimeCostPerMinute": 0.4},
            {"nodeId": "node-spot-pricier", "cloudProvider": "AWS", "instanceType": "m5.large", "totalCapacity": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "nodeType": "SPOT", "realTimeCostPerMinute": 0.6}
        ]
        
        best_node = select_best_node(job, nodes)
        self.assertIsNotNone(best_node)
        self.assertEqual(best_node['nodeId'], "node-spot-cheaper")

    def test_gpu_job_matches_correct_node(self):
        """
        Test case: A job requiring a specific GPU type is correctly matched to a node with that GPU.
        """
        job = {
            "jobId": "job-gpu",
            "priority": 8,
            "resourceRequest": {"cpu": 16, "memory_gb": 64, "gpuType": "V100", "gpuCount": 1},
            "slaType": "BATCH",
            "maxTolerableCost": 3.0,
            "isRescheduled": False
        }
        nodes = [
            # Node with a different GPU type
            {"nodeId": "node-A100", "cloudProvider": "AWS", "instanceType": "p4.large", "totalCapacity": {"cpu": 32, "memory_gb": 128, "gpuType": "A100", "gpuCount": 1}, "allocatable": {"cpu": 32, "memory_gb": 128, "gpuType": "A100", "gpuCount": 1}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 2.8},
            # Node with the correct GPU type
            {"nodeId": "node-V100", "cloudProvider": "GCP", "instanceType": "n1-standard-16", "totalCapacity": {"cpu": 32, "memory_gb": 128, "gpuType": "V100", "gpuCount": 1}, "allocatable": {"cpu": 32, "memory_gb": 128, "gpuType": "V100", "gpuCount": 1}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 2.5}
        ]

        best_node = select_best_node(job, nodes)
        self.assertIsNotNone(best_node)
        self.assertEqual(best_node['nodeId'], "node-V100")

    def test_run_scheduling_cycle_integration(self):
        """
        Test that run_scheduling_cycle correctly processes multiple jobs
        and updates node and job states.
        """
        jobs_to_schedule = [
            {"jobId": "job-1", "priority": 10, "resourceRequest": {"cpu": 8, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "slaType": "BATCH", "maxTolerableCost": 1.0, "isRescheduled": False},
            {"jobId": "job-2", "priority": 5, "resourceRequest": {"cpu": 8, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "slaType": "BATCH", "maxTolerableCost": 1.0, "isRescheduled": False}
        ]
        nodes_for_scheduling = [
            {"nodeId": "node-1", "totalCapacity": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 0.8},
            {"nodeId": "node-2", "totalCapacity": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 0.6}
        ]
        
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs_to_schedule, f, indent=2)
        with open(NODES_FILE, 'w') as f:
            json.dump(nodes_for_scheduling, f, indent=2)
            
        run_scheduling_cycle(jobs_to_schedule, nodes_for_scheduling)
        
        updated_jobs = json.load(open(JOBS_FILE, 'r'))
        updated_nodes = json.load(open(NODES_FILE, 'r'))

        # Job 1 is high priority and should be scheduled first
        self.assertTrue(updated_jobs[0].get('isScheduled'))
        self.assertFalse(updated_jobs[1].get('isScheduled'))

        # Job 1 is scheduled on the cheaper node
        self.assertEqual(updated_nodes[0]['allocatable']['cpu'], 0)
        self.assertEqual(updated_nodes[0]['nodeId'], 'node-2')
        self.assertEqual(updated_nodes[1]['allocatable']['cpu'], 8)
        self.assertEqual(updated_nodes[1]['nodeId'], 'node-1')


if __name__ == '__main__':
    unittest.main()
