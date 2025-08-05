**Cost-Aware Distributed Job Scheduler PoC**
============================================

This repository contains a Python-based Proof of Concept (PoC) for a cost-aware distributed job scheduler. It simulates the core logic of assigning machine learning jobs to compute nodes, considering factors like job priority, SLA type, node cost (including spot instances), and available resources. It also includes a mechanism to simulate job completion and node resource freeing.

**Project Structure**
---------------------

*   scheduler\_poc.py: The main Python script containing the scheduler's core logic, including job-to-node assignment, resource allocation, and a background process for node resource resetting.
    
*   jobs.json: A JSON file representing the queue of jobs waiting to be scheduled. You can modify this file to define different job types and requirements.
    
*   nodes.json: A JSON file representing the available compute nodes in your cluster. You can modify this file to define various node types, capacities, and costs.
    
*   test\_scheduler.py: A suite of unit tests to verify the correctness of the select\_best\_node function and the overall run\_scheduling\_cycle logic.
*   Run the script:
```bash
python scheduler_poc.py
```

    

**How to Run the Scheduler Simulation**
---------------------------------------

To run the scheduler and observe its behavior:

1.  **Save the files:** Ensure scheduler\_poc.py, jobs.json, and nodes.json are all in the same directory.
    
2.  **Open your terminal or command prompt.**
    
3.  **Navigate to the directory** where you saved the files.
    
4.  **Run the script:**python scheduler\_poc.pyThe scheduler will start running in a continuous loop, printing its actions to the console. It will attempt to schedule jobs, update node resources, and periodically "free up" nodes to simulate job completion.
    

**How to Run Unit Tests**
-------------------------

To verify the core logic of the scheduler:

1.  **Save the files:** Ensure test\_scheduler.py is in the same directory as scheduler\_poc.py, jobs.json, and nodes.json.
    
2.  **Open your terminal or command prompt.**
    
3.  **Navigate to the directory** where you saved the files.
4.  **Run the tests**
```bash
python -m unittest test_scheduler.py
```

The tests will execute and provide a summary of passed and failed tests. This allows you to quickly check if the scheduler's logic is behaving as expected under various predefined scenarios.

