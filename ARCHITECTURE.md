Cost-Aware Distributed Job Scheduler Architecture
=================================================


1\. System Architecture & Components
------------------------------------

### C4 Container Diagram
![C4 Container Diagram](https://www.plantuml.com/plantuml/png/TLP1Szis4xthLsny-UGPMvhvsbDxYIEvcRHHgqhjv9W1mJM96WGOx4AAfzF_NYm8QSYOlTZ43l7sxTktIxqbLe5ZPnTlkCKEWOmzOLYyCKxRM2Eqp3tzi5u7TLurXjjOHSAWlMDqlDA-M_TMEK6u9wwjgTQRx-_t4lfpzt7TAM8CAVHvasueup2iUics-1ziyIcT8QM57drl4PO2JRUWN2rX4o2WLMoyezRqjDXZ8E-MjM9rr2RbDyHtSBDDPxW6RbBa6AlEC6MWpZl3FX1qIhUIqA8AphW6_l8LhMvk5ySNOkm-FtxbfRO-rllWJwR6a80sSePB01xs7qZmIu0WrTz7HZ2EM3cT8ajSDQixUFXqXCVD_-_W_MOFc_BMeskCmw6-3bb98K0OJaPZPZ9LXJ8lg7nqjGel5vxlodb9kiKwse6e9xv_EAk0i3N4mLGfOGq_-mgEbzTkRk7lnG80O996Npf3S3QS99fDBjUkFLogtdnmJK2Yb3kf0kKauhptefCy7L2ZEI69qa3I4oBZ7GJy4f4uYNLuFFwnRWxxpQsKFysHBlqUCM82aZBoiw3-efwUbJniOr2LHUYGI3K8oPdmv0CObzeoRl0KzohRnWS1l-e34hXKqFVMwEmzYUpKyr36FVjxvsk4tYgD7Jg66hMHiWWgHLY3Tw20j0z20NFBNvCu-_0i3BekEidZfOcVSX36qQcWLzyf9w5ShJHhMWAm1q9NYpixvMgIGC5-QD3nZ2XIqv4LuquvrMHB_IfbvXYKO25p71oRtG8_cO34adNxBYkLNwLCAw2ozsnagsGO_mJAsklGICuPAcK6KuRVWj8MHsCeMOVW79MDIZACPHeHa95hZH0rMbdeqpzfJvx0f-0xo5cXBvF-cjQsMbAh0jR7XA6QR9nyXXB8U-Sxy26D_54E4Y_UJxpqS--Duy6XVK3iUXvcGViJXfV_iaXkM48Rzo_N-C9jkhvLs0qMFKH7a2AOL9X8_2FWLzJfbBdG7GJiVM3AJOdfdBL9VopIY9aG-cUwaQRh62haCs9U5pcXT-AjnG7jjojwiYxASXOobqq09wDIEhavVdMq0VQniePQ971updK0-tH5xamdUd8jgKcnAvNdHjz1Zy7uMcnWNw3treeHf2k2BA8ds1dKcGb9MOB1eQKwXe2EvRLYztcO6NUFOUJwn9tpABFhuuYkfj5YaezIY5eQDX9hxkhKQXbdl3p4NjTDNGXDhineSoWcomMrg2otsMW1oSUW4QBix0A-Bot9IqqQGtDPllquxygN_TkHSfwDHihflXHjBn_ewtTNqdwu17SbAFddCh-QV7MQcMpsmmvOfmLGa3BKQtMcbKmTS6LQ8ojZSnbbL6ykgt2CFY4wdJlPGG5LHs1zau6a_63qXUjkEAq_-gOHmms_C1BoMtHrxEo_)
The following diagram provides a high-level overview of the major components and their interactions.

### Component Descriptions

-   **API Ingress** Stateless entry point for job submissions (REST or gRPC). Publishes validated jobs to the Job Queue.

-   **Job Queue (e.g., Kafka, RabbitMQ)** High-throughput message bus and durable buffer for incoming jobs. Decouples job submission from scheduling and ensures resilience.

-   **Scheduler Core** The system's central component. Selects the best node for a job using an in-memory backlog, node state, and pricing data to run a complex scoring algorithm.

-   **Node State Manager** Maintains real-time state of all compute nodes. Aggregates data from Worker Agents and Cloud Provider APIs to track capacity, resources, and health.

-   **Cloud Price Oracle** Provides real-time and historical pricing for cloud instance types. Normalizes costs for the scoring engine to enable cost-aware decisions.

-   **Worker Agent** Local software on each node that executes jobs, monitors resource usage, and reports node status to the Node State Manager. Monitors for preemption notices on spot instances.

-   **Worker Communicator** Provides the API for the Scheduler Core to send job placement instructions to the Worker Agent. Acts as a gateway for communication with the worker fleet.

2\. Data Models
---------------

### Job Data Model

The Job entity represents a user's request for a machine learning task.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`
```json
{

 "jobId": "uuid-v4-string",

 "priority": 7,                  // Integer from 1 (low) to 10 (high)

 "resourceRequest": {

 "cpu": 8,                     // Number of cores

 "memory_gb": 32,              // Memory in GB

 "gpuType": "A100",            // Optional: e.g., "A100", "V100"

 "gpuCount": 1

 },

 "slaType": "LATENCY_SENSITIVE",  // Enum: "BATCH" or "LATENCY_SENSITIVE"

 "maxTolerableCost": 1.50,        // Max cost per minute the user is willing to pay

 "isRescheduled": false          // New field to indicate if the job was previously evicted

}
```


### Node Data Model

The Node entity represents a single compute instance in the cluster.

```json
{

 "nodeId": "aws-ec2-id-12345",

 "cloudProvider": "AWS",             // Enum: "AWS", "GCP", "AZURE"

 "instanceType": "p3.2xlarge",       // e.g., "c5.2xlarge" or "g4dn.2xlarge"

 "totalCapacity": {

 "cpu": 64,

 "memory_gb": 256,

 "gpuType": "A100",

 "gpuCount": 2

 },

 "allocatable": {

 "cpu": 32,

 "memory_gb": 128,

 "gpuCount": 1

 },

 "nodeType": "ON_DEMAND",          // Enum: "ON_DEMAND" or "SPOT"

 "realTimeCostPerMinute": 2.50

}
```

3\. The Scheduling Logic & Decision Engine
------------------------------------------

### Algorithm Overview

The **Scheduler Core** follows a continuous loop:

1.  **Poll Jobs:** Pull a small batch of high-priority jobs from the **Job Queue** into an in-memory backlog.

2.  **Select Best Job:** Pick the highest-priority job from the backlog to schedule.

3.  **Filter Nodes:** Filter out nodes that cannot satisfy the job's hard requirements (e.g., resource capacity, GPU type).

4.  **Score Nodes:** For each remaining node, calculate a comprehensive fitness score based on multiple factors.

5.  **Select Best Node:** Choose the node with the highest score. If no node meets the minimum score threshold, the job is not scheduled and remains in the backlog.

6.  **Place Job:** Send the placement instruction to the **Worker Agent** via the **Worker Communicator**.

### Assumptions and Scoring Considerations

To simplify the initial design and focus on the core logic, the following reasonable assumptions were made for the Proof of Concept (PoC) and the scoring model:

-   **Job Backlog:** The Scheduler Core maintains a bounded in-memory backlog of jobs. For the PoC, a size of **500 jobs** is assumed to be an efficient balance between having a wide selection of jobs to choose from and maintaining a low memory footprint (assuming an average job size of ~50KB, this results in a 25MB memory usage).

-   **Job Prioritization:** The priority scale is assumed to be an integer from **1 (lowest) to 10 (highest)**.

-   **Node Count:** The system operates with a static number of nodes for the PoC, with a total of **25 nodes** consisting of various types (e.g., On-Demand, Spot, GPU-enabled).

-   **Cost Normalization:** The CostScore is normalized against an assumed maximum node cost. For the PoC, a maximum cost of **$5.00/minute** is used for this normalization.

-   **Scoring Weights:** The weights for the scoring function (w_1, w_2, w_3, w_4, w_5) are fixed for the PoC to demonstrate the core logic. They can be tuned later based on real-world performance data.

### Scoring Framework

The scoring algorithm is the heart of the scheduler. It calculates a weighted score for each (Job, Node) pair. The function is defined as:

Score(job,node)=(w_1cdotCostScore)+(w_2cdotPriorityScore)+(w_3cdotSLAScore)+(w_4cdotRescheduleBonus)+(w_5cdotResourceScore)

-   **CostScore**: A function that normalizes the node's cost. Lower cost yields a higher score. This is a critical factor for optimizing expenditure. A hard constraint is applied here: if a node's cost exceeds job.maxTolerableCost, its score is 0.

-   **PriorityScore**: Directly proportional to the job's priority. This ensures that higher-priority jobs are always considered first and are more likely to be scheduled on the best-fitting, even if more expensive, nodes.

-   **SLAScore**: A critical factor for handling volatility.

    -   For LATENCY_SENSITIVE jobs, a large negative penalty is applied if the node is a SPOT instance, heavily discouraging this match.

    -   For BATCH jobs, a small positive bonus is applied if the node is a SPOT instance, encouraging cost savings for jobs that can tolerate preemption.

-   **RescheduleBonus**: This is a new component that directly addresses starvation for jobs evicted from spot instances. The score is a boolean value (1 if job.isRescheduled is true, 0 otherwise). This provides a significant boost to a job that has already experienced a preemption, ensuring it is prioritized and rescheduled quickly. The weight, w_4, is set to be higher than other weights to make this a dominant factor when a job needs to be rescheduled.

-   **ResourceScore**: This is a new factor that ensures efficient resource utilization and better scheduling for high-priority jobs. It is calculated by normalizing the available resources on a node. A node with a higher percentage of available resources (CPU, Memory, GPU) will receive a higher score. This makes nodes with more "free" capacity more attractive, especially for large, high-priority jobs.

The weights (w_1, w_2, w_3, w_4, w_5) are configurable and tuned based on business priorities. For example, w_4 and w_5 would be given a high value to ensure jobs that have been previously evicted and nodes with more available resources are prioritized.

### Handling Volatility

The system's resilience to spot instance preemption is handled through a coordinated workflow:

1.  **Preemption Notice:** The **Worker Agent** running on a spot instance continuously polls a cloud provider metadata endpoint. Upon receiving a preemption notice (e.g., AWS's 2-minute notice), it initiates a graceful shutdown.

2.  **Graceful Shutdown & Checkpointing:** The Worker Agent instructs the running job to pause and save its current state (a "checkpoint") to a durable, shared storage location (e.g., S3).

3.  **Reschedule Trigger:** The Worker Agent sends a notification to the **Scheduler Core**. The scheduler then pushes the job back into the **Job Queue** with the isRescheduled flag set to true and a highly elevated priority.

4.  **New Scheduling Decision:** The scheduler's continuous loop will quickly pick up this high-priority, evicted job. The RescheduleBonus and the new ResourceScore in the scoring framework will ensure it is prioritized on a node that can accommodate it efficiently. It will then find a new, available node, potentially preferring a more reliable On-Demand instance for the second attempt, to prevent further interruptions.

5.  **Job Resumption:** The new Worker Agent tasked with running the job checks for a pre-existing checkpoint and resumes the job's execution from where it left off, minimizing progress loss.

### Starvation Prevention

To ensure that low-priority jobs are not indefinitely delayed, the scheduler employs a **priority aging** and **starvation sweep** mechanism.

-   The scheduler maintains a bounded, prioritized backlog of jobs. In its normal operation, it prioritizes pulling jobs from the queue based on their priority.

-   A periodic background task or a built-in heuristic monitors the age of jobs in the queue.

-   After a configurable timeout (e.g., 2 hours), a low-priority job's effective priority is artificially increased.

-   Additionally, every N polling cycles, the scheduler performs a "starvation sweep," specifically pulling the oldest jobs from the queue regardless of their priority to ensure they get an opportunity to be scheduled.

4\. Scalability and Resilience
------------------------------

### High Availability

The **Scheduler Core** itself is designed as a distributed, stateless service with a leader election mechanism (e.g., using a protocol like Raft or an external service like Zookeeper).

-   Multiple instances of the Scheduler Core run concurrently.

-   One instance is elected as the leader and is responsible for making all scheduling decisions.

-   The other instances act as followers. If the leader fails, a new leader is automatically elected, ensuring minimal downtime and avoiding a single point of failure.

### State Management

The scheduler is designed to be largely stateless. All critical state is persisted in a highly available, distributed database (e.g., Firestore, Cassandra).

-   **Job State:** The Job Queue itself serves as the primary state for unscheduled jobs.

-   **Node State:** The Node State Manager persists the state of all nodes in the database.

-   **Recovery:** Upon a restart, a new scheduler instance can re-initialize its in-memory backlog by polling the **Job Queue** and its view of the cluster by querying the **Node State Manager's** persisted data.

### Extensibility

The design uses a plugin-based architecture with clear interfaces, allowing for future expansion with minimal code changes.

-   **Cloud Provider Interface:** A new cloud provider can be added by implementing a CloudProvider interface, which encapsulates the logic for fetching pricing, node state, and communicating with its specific APIs.

-   **Scheduling Strategy Interface:** The core scoring engine can be designed to accept different scheduling strategy plugins. This allows for A/B testing new algorithms (e.g., a "data locality" scheduler) or for customizing scheduling behavior for specific workloads without modifying the core system.