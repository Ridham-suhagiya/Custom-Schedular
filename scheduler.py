import json
import time
import random
import os

# --- Configuration ---
# Reset interval for nodes (in seconds)
RESET_INTERVAL = 10 
# Path to data files
JOBS_FILE = 'jobs.json'
NODES_FILE = 'nodes.json'

# Weights for the scoring function
WEIGHTS = {
    'cost': 0.2,
    'priority': 0.3,
    'sla': 0.2,
    'reschedule': 0.2,
    'resource': 0.1,
}

# Assumed max cost for score normalization
MAX_COST = 5.00 

def read_data(file_path):
    """Reads and returns data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON file.")
        return []

def write_data(file_path, data):
    """Writes data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_score(job, node):
    """
    Calculates the weighted fitness score for a given job and node.
    This function mirrors the logic from the React PoC.
    """
    # CostScore: Inversely proportional to cost (normalized against max cost)
    cost_score = 1 - (node['realTimeCostPerMinute'] / MAX_COST)

    # PriorityScore: Directly proportional to job priority (normalized)
    priority_score = job['priority'] / 10.0

    # SLAScore: Penalty for LATENCY_SENSITIVE jobs on SPOT nodes, bonus for BATCH jobs.
    sla_score = 0
    if job['slaType'] == 'LATENCY_SENSITIVE' and node['nodeType'] == 'SPOT':
        sla_score = -1
    elif job['slaType'] == 'BATCH' and node['nodeType'] == 'SPOT':
        sla_score = 0.5

    # RescheduleBonus: High bonus for jobs that were previously evicted.
    reschedule_bonus = 1 if job['isRescheduled'] else 0

    # ResourceScore: Higher score for nodes with more available resources.
    total_capacity = node['totalCapacity']['cpu'] + node['totalCapacity']['memory_gb'] + (node['totalCapacity']['gpuCount'] or 0)
    allocatable_capacity = node['allocatable']['cpu'] + node['allocatable']['memory_gb'] + (node['allocatable']['gpuCount'] or 0)
    resource_score = allocatable_capacity / total_capacity if total_capacity > 0 else 0

    # Calculate the final weighted score
    final_score = (
        (WEIGHTS['cost'] * cost_score) +
        (WEIGHTS['priority'] * priority_score) +
        (WEIGHTS['sla'] * sla_score) +
        (WEIGHTS['reschedule'] * reschedule_bonus) +
        (WEIGHTS['resource'] * resource_score)
    )

    # Ensure score is not negative
    return max(0, final_score)

def select_best_node(job, nodes):
    """
    Finds the best-fit node for a given job based on the scoring function.
    Returns the best node and its score, or None if no suitable node is found.
    """
    best_node = None
    highest_score = -1

    for node in nodes:
        # Hard filter 1: Check if the node's cost is acceptable for the job.
        if node['realTimeCostPerMinute'] > job['maxTolerableCost']:
            continue # Skip this node if it's too expensive.

        # Hard filter 2: Check if node can satisfy the job's resource requirements
        can_fit = (
            node['allocatable']['cpu'] >= job['resourceRequest']['cpu'] and
            node['allocatable']['memory_gb'] >= job['resourceRequest']['memory_gb'] and
            (job['resourceRequest']['gpuType'] is None or (node['totalCapacity']['gpuType'] == job['resourceRequest']['gpuType'] and node['allocatable']['gpuCount'] >= job['resourceRequest']['gpuCount']))
        )

        if can_fit:
            score = calculate_score(job, node)
            if score > highest_score:
                highest_score = score
                best_node = node
    
    return best_node

def reset_jobs(jobs):
    """Resets the 'isScheduled' flag for all jobs."""
    print("Resetting all jobs for a new scheduling cycle...")
    for job in jobs:
        if 'isScheduled' in job:
            job['isScheduled'] = False
    return jobs

def run_scheduling_cycle(jobs, nodes):
    """
    Runs one cycle of the scheduling algorithm.
    """
    print("\n--- Running a Scheduling Cycle ---")
    
    # Sort jobs by priority (descending)
    sorted_jobs = sorted(jobs, key=lambda j: j['priority'], reverse=True)
    
    # Keep track of updated nodes for writing back to file
    updated_nodes = {node['nodeId']: node.copy() for node in nodes}
    
    for job in sorted_jobs:
        # Check if the job has already been scheduled in this or a previous cycle
        if 'isScheduled' in job and job['isScheduled']:
            continue

        best_node = select_best_node(job, list(updated_nodes.values()))
        
        if best_node:
            print(f"  -> Job '{job['jobId']}' scheduled on node '{best_node['nodeId']}'")
            
            # Update allocatable resources in our temporary dictionary
            updated_nodes[best_node['nodeId']]['allocatable']['cpu'] -= job['resourceRequest']['cpu']
            updated_nodes[best_node['nodeId']]['allocatable']['memory_gb'] -= job['resourceRequest']['memory_gb']
            if job['resourceRequest']['gpuCount'] > 0:
                updated_nodes[best_node['nodeId']]['allocatable']['gpuCount'] -= job['resourceRequest']['gpuCount']
            
            # Mark the job as scheduled to prevent it from being scheduled again
            job['isScheduled'] = True
        else:
            print(f"  -> Job '{job['jobId']}' could not be scheduled.")

    # Convert the updated nodes back to a list for writing
    final_nodes = list(updated_nodes.values())
    write_data(NODES_FILE, final_nodes)
    
    # Update the jobs file with the 'isScheduled' flag
    write_data(JOBS_FILE, jobs)
    print("Scheduling cycle complete. Node and Job states updated.")

def reset_node_resources(nodes):
    """
    Simulates a job finishing by resetting the resources of a random node
    that currently has a job allocated.
    """
    nodes_with_jobs = [
        node for node in nodes
        if node['allocatable']['cpu'] < node['totalCapacity']['cpu'] or
           node['allocatable']['memory_gb'] < node['totalCapacity']['memory_gb'] or
           (node['totalCapacity']['gpuCount'] is not None and node['allocatable']['gpuCount'] < node['totalCapacity']['gpuCount'])
    ]

    if nodes_with_jobs:
        node_to_reset = random.choice(nodes_with_jobs)
        print(f"\n--- Node Updater: Resetting resources for '{node_to_reset['nodeId']}' ---")
        
        # Reset allocatable resources to total capacity
        node_to_reset['allocatable'] = node_to_reset['totalCapacity'].copy()
        
        # Write the updated nodes back to the file
        write_data(NODES_FILE, nodes)
        return True
    else:
        print("\n--- Node Updater: All nodes are free. Nothing to reset. ---")
        return False

def main():
    """
    Main loop to run the scheduler and node updater.
    """
    print("Starting the Cost-Aware Distributed Job Scheduler PoC...")
    
    last_reset_time = time.time()
    
    while True:
        # Read the current state of jobs and nodes
        jobs = read_data(JOBS_FILE)
        nodes = read_data(NODES_FILE)

        # Reset jobs before each cycle
        jobs = reset_jobs(jobs)

        # Run one scheduling cycle
        run_scheduling_cycle(jobs, nodes)

        # Periodically reset nodes to simulate job completion
        if time.time() - last_reset_time >= RESET_INTERVAL:
            reset_node_resources(nodes)
            last_reset_time = time.time()
        
        print("\nWaiting for 5 seconds for the next cycle...")
        time.sleep(5)

if __name__ == "__main__":
    main()
