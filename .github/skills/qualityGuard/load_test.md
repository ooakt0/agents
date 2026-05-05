# Skill: Load Tests

## ROLE & ACTIVATION
You are **@qualityGuard** running load tests. Activate this skill FOURTH in the quality chain �
after integration_test completes. Verify the system meets SLOs under realistic load before
running the penetration scan.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` � Performance SLOs from the Reliability and Observability ADRs
- `.github/shared/standards.md` �3 � SLO requirements (P99 < 1000ms, error rate < 0.1%)
- All Lambda handler entry points to identify which endpoints to target

## PROCESS

### Step 1: Define Load Test Scenarios
Identify the critical user paths and define load scenarios:

| Scenario | Virtual Users | Duration | Target Endpoint |
|----------|--------------|----------|-----------------|
| Steady state | 10 | 60s | Primary handler |
| Ramp up | 10?100 | 120s | Primary handler |
| Spike | 200 | 30s | Primary handler |
| DLQ depth check | 50 | 60s | All handlers |

### Step 2: Create Artillery Configuration
Write `tests/load/artillery.yml`:
```yaml
config:
  target: '{{ $processEnvironment.API_ENDPOINT }}'
  http:
    timeout: 10
  phases:
    - name: 'warm-up'
      duration: 30
      arrivalRate: 5
    - name: 'steady-state'
      duration: 60
      arrivalRate: 10
    - name: 'ramp'
      duration: 120
      arrivalRate: 10
      rampTo: 100
  ensure:
    p99: 1000
    maxErrorRate: 0.1

scenarios:
  - name: 'Process Order'
    flow:
      - post:
          url: '/orders'
          json:
            customerId: 'cust-{{ $randomNumber(1, 100) }}'
            amount: '{{ $randomNumber(10, 500) }}'
          expect:
            - statusCode: 200
            - contentType: json
```

### Step 3: Run Load Test
Execute the Artillery test against the staging environment:
```bash
npx artillery run tests/load/artillery.yml --output tests/load/results.json
npx artillery report tests/load/results.json --output tests/load/report.html
```

### Step 4: Evaluate Results Against SLOs

Parse the Artillery output and check each SLO:

**P99 Latency SLO: < 1000ms**
```
? PASS: p99 latency = [X]ms � within SLO of 1000ms
? FAIL: p99 latency = [X]ms � SLO BREACHED (1000ms limit)
```

**Error Rate SLO: < 0.1%**
```
? PASS: error rate = [X]% � within SLO of 0.1%
? FAIL: error rate = [X]% � SLO BREACHED (0.1% limit)
```

**DLQ Depth Check:**
After the load test completes, check the DLQ message count:
```
? PASS: DLQ depth = 0 � no messages routed to DLQ under load
? FAIL: DLQ depth = [N] � messages routed to DLQ under load � investigate
```

### Step 5: Lambda Concurrency Check
Verify Lambda concurrency metrics from CloudWatch during the load test:
- Check for throttling events (`Throttles` metric > 0)
- Check for cold start rate (if > 10%, consider provisioned concurrency)

```
? PASS: Lambda throttles = 0
??  WARN: Cold start rate = [X]% � consider provisioned concurrency
? FAIL: Lambda throttles = [N] � reserved concurrency limit reached
```

## OUTPUT CONTRACT

**If P99 > 1000ms or error rate > 0.1% or DLQ depth > 0:**
- Flag findings to @architect for right-sizing (Lambda memory, DynamoDB capacity, concurrency limits)
- Do NOT proceed to penetration_scan
- Write: `Load test FAILED: [findings summary]. Flagging to @architect for right-sizing.`

**If all SLOs pass:**
1. Save `tests/load/results.json` and `tests/load/report.html`
2. Write SLO results summary to `.github/shared/project_state.md` under the task
3. Write this exact phrase to signal completion:
   `Load tests complete. Activating penetration_scan.`
