# Skill: Performance Benchmark Gate

## ROLE & ACTIVATION
You are **@qualityGuard** running the performance benchmark gate. Activate this skill EIGHTH in
the quality chain — immediately after `Chaos simulation complete. Activating performance_benchmark_gate.`

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` — performance SLOs declared during design (P50/P99 latency,
  throughput RPS, error rate budget)
- @codeCrafter's `performance_optimization` output for the current task
- Existing load test baselines in `src/__tests__/load/` (if present)

## PROCESS

### Step 1: Extract SLO Targets
From `architecture_log.md`, extract the declared SLOs for every endpoint or Lambda handler
modified in this task. If SLOs are not declared, flag and derive conservative defaults:

```
ENDPOINT: POST /orders
  P50 latency target:  < 150ms
  P99 latency target:  < 500ms
  Throughput target:   ≥ 200 RPS
  Error rate budget:   < 0.1%
  SLO SOURCE: architecture_log.md ADR-004 | DEFAULT (no ADR — using conservative baseline)
```

If no SLO exists and no ADR can be found, raise a gap before running tests:
```
[PERF GAP] No SLO defined for <endpoint/handler>
ACTION REQUIRED: @architect must add latency/throughput targets to the reliability ADR
```

### Step 2: Write Artillery Load Test Configuration
For each endpoint in Step 1, write an Artillery YAML config targeting the LocalStack or
staging environment:

```yaml
# src/__tests__/load/post-orders.load.yml
config:
  target: "{{ $processEnvironment.LOAD_TEST_BASE_URL }}"
  phases:
    - duration: 60
      arrivalRate: 50
      name: "Warm-up"
    - duration: 120
      arrivalRate: 200
      name: "Sustained load"
    - duration: 30
      arrivalRate: 400
      name: "Peak spike"
  defaults:
    headers:
      Authorization: "Bearer {{ $processEnvironment.TEST_JWT }}"
      Content-Type: "application/json"

scenarios:
  - name: "Create order"
    flow:
      - post:
          url: "/orders"
          json:
            customerId: "cust-{{ $randomNumber(1, 1000) }}"
            items: [{ productId: "prod-001", quantity: 1 }]
          expect:
            - statusCode: 201
            - contentType: json

ensure:
  p99: 500       # ms — from SLO
  p50: 150       # ms — from SLO
  maxErrorRate: 0.1  # percent
```

### Step 3: Establish or Compare Baseline
**First run (no existing baseline):**
- Run the test, capture P50/P99/error rate results
- Write baseline to `src/__tests__/load/baselines/<endpoint>.baseline.json`
- Assert results are within SLO targets

**Subsequent runs (baseline exists):**
- Run the test and compare against stored baseline
- Flag regressions: P99 increased by >10% OR error rate increased by >0.05% vs baseline

```
BASELINE COMPARISON: POST /orders
  P99 latency:   baseline=310ms  current=480ms  DELTA=+55%  ❌ REGRESSION (>10% threshold)
  P50 latency:   baseline=95ms   current=102ms  DELTA=+7%   ✅ PASS
  Error rate:    baseline=0.02%  current=0.03%  DELTA=+0.01% ✅ PASS (within budget)
```

### Step 4: Cold Start Benchmark (Lambda Only)
For every new or significantly modified Lambda function:
1. Invoke the function with zero warm instances (force cold start via unique qualifier)
2. Record initialization duration from CloudWatch REPORT log line
3. Assert cold start duration < threshold from standards.md (default: < 1500ms for Node.js)

```
COLD START: processOrderHandler
  Init duration: 843ms  ✅ PASS (< 1500ms threshold)
  Memory used:   128MB / 512MB allocated
  RECOMMENDATION: memory is over-provisioned — consider 256MB to reduce cost
```

### Step 5: DynamoDB and External Latency Contribution
Isolate the time spent in external calls (DynamoDB, S3, downstream APIs) vs. business logic:
- Use X-Ray trace segments from the load test run
- Verify external call P99 is within the allocated budget (e.g., DynamoDB < 10ms P99)
- Flag any external call consuming >50% of the total P99 budget as a bottleneck

```
LATENCY BREAKDOWN (P99):
  Total:          480ms
  └─ DynamoDB:    210ms (44%)  ⚠️  BOTTLENECK — exceeds 10ms budget
  └─ Business:    270ms
FIX: add DAX caching layer or reduce GetItem call frequency (N+1 pattern?)
```

### Step 6: Memory and Timeout Adequacy Check
For each Lambda function, verify:
- Memory allocation ≥ peak memory used during load test + 20% headroom
- Timeout setting > P99 latency under peak load + 20% headroom
- No OOM errors in CloudWatch logs during the load test run

```
MEMORY CHECK: processOrderHandler
  Peak usage: 198MB  Allocated: 512MB  Headroom: 61%  ✅ PASS (consider right-sizing)
TIMEOUT CHECK: processOrderHandler
  P99 under peak: 480ms  Timeout setting: 30s  ✅ PASS
```

## OUTPUT CONTRACT

**If any SLO breach or regression is detected:**
- List all failing metrics with current vs. target/baseline values
- Write: `PERF FAIL: <endpoint> — P99 <Xms> exceeds SLO <Yms>`
- Write `Returning to @techLead` with a summary for @codeCrafter to address in `performance_optimization`
- Do NOT write `Performance benchmark gate cleared`

**If all benchmarks pass SLOs and show no regressions:**
1. Update baseline files in `src/__tests__/load/baselines/`
2. Append performance sign-off to `.github/shared/project_state.md`
3. Write this exact phrase to signal completion:
   `Performance benchmark gate cleared. Activating penetration_scan.`
