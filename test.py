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
        and updates node and job states, demonstrating resource contention.
        """
        jobs_to_schedule = [
            {"jobId": "job-1", "priority": 10, "resourceRequest": {"cpu": 8, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "slaType": "BATCH", "maxTolerableCost": 1.0, "isRescheduled": False},
            {"jobId": "job-2", "priority": 5, "resourceRequest": {"cpu": 8, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "slaType": "BATCH", "maxTolerableCost": 1.0, "isRescheduled": False}
        ]
        nodes_for_scheduling = [
            # node-A is too small for either job (needs 8 CPU, has 4 CPU)
            {"nodeId": "node-A", "totalCapacity": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 4, "memory_gb": 16, "gpuType": None, "gpuCount": 0}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 0.8},
            # node-B is large enough for one job
            {"nodeId": "node-B", "totalCapacity": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "allocatable": {"cpu": 8, "memory_gb": 32, "gpuType": None, "gpuCount": 0}, "nodeType": "ON_DEMAND", "realTimeCostPerMinute": 0.6}
        ]
        
        # Write initial data to files
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs_to_schedule, f, indent=2)
        with open(NODES_FILE, 'w') as f:
            json.dump(nodes_for_scheduling, f, indent=2)
            
        # Run the scheduling cycle
        # Note: run_scheduling_cycle modifies the lists in place and writes to files
        run_scheduling_cycle(jobs_to_schedule, nodes_for_scheduling) 
        
        # Reload data from files to get the true, updated state after the function call
        updated_jobs = json.load(open(JOBS_FILE, 'r'))
        updated_nodes = json.load(open(NODES_FILE, 'r'))

        # Verify job scheduling status
        job1_in_updated = next((j for j in updated_jobs if j['jobId'] == 'job-1'), None)
        job2_in_updated = next((j for j in updated_jobs if j['jobId'] == 'job-2'), None)

        self.assertIsNotNone(job1_in_updated, "Job 1 should be present in updated jobs.")
        self.assertIsNotNone(job2_in_updated, "Job 2 should be present in updated jobs.")

        self.assertTrue(job1_in_updated.get('isScheduled', False), "Job 1 (high priority) should be scheduled.")
        self.assertFalse(job2_in_updated.get('isScheduled', False), "Job 2 (low priority) should not be scheduled due to resource contention.")

        # Verify node resource allocation
        node_a_updated = next((n for n in updated_nodes if n['nodeId'] == 'node-A'), None)
        node_b_updated = next((n for n in updated_nodes if n['nodeId'] == 'node-B'), None)

        self.assertIsNotNone(node_a_updated, "Node A should be present in updated nodes.")
        self.assertIsNotNone(node_b_updated, "Node B should be present in updated nodes.")

        # Job-1 (priority 10) should be scheduled on node-B (cheaper and fits)
        # Node-B's resources should be reduced by job-1's request (8 CPU, 16GB Memory)
        self.assertEqual(node_b_updated['allocatable']['cpu'], 0, "Node B CPU should be 0 after scheduling Job 1.")
        self.assertEqual(node_b_updated['allocatable']['memory_gb'], 16, "Node B Memory should be 16 after scheduling Job 1.")

        # Node-A's resources should remain unchanged as it's too small for either job
        self.assertEqual(node_a_updated['allocatable']['cpu'], 4, "Node A CPU should remain 4.")
        self.assertEqual(node_a_updated['allocatable']['memory_gb'], 16, "Node A Memory should remain 16.")



if __name__ == '__main__':
    unittest.main()
