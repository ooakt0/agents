# Skill: Pipeline Setup

## ROLE & ACTIVATION
You are **@devOps** setting up the CI/CD pipeline. Activate this skill FIRST in the deployment
chain � after @techLead delegates following AUDIT_RESULT passing.

## INPUTS
Before starting, read:
- `.github/shared/architecture_log.md` � all ADRs (stack names, environments, alarm names)
- `.github/shared/project_state.md` � environment names, CDK stack names
- `.github/shared/standards.md` �1 � AWS, IAM, and security requirements

## PROCESS

### Step 1: Create GitHub Actions Workflow File
Write `.github/workflows/deploy.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage --ci
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/

  deploy-dev:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.DEV_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - run: npm ci
      - run: npx cdk deploy --app "npx ts-node bin/app.ts" --context env=dev --require-approval never

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.STAGING_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - run: npm ci
      - run: npx cdk deploy --app "npx ts-node bin/app.ts" --context env=staging --require-approval never
```

### Step 2: Configure OIDC Trust in AWS
OIDC allows GitHub Actions to assume an IAM role without storing long-lived credentials.
Write the CDK snippet for the OIDC provider and deploy role (add to the infra stack):

```typescript
const githubOidcProvider = new iam.OpenIdConnectProvider(this, 'GithubOidc', {
  url: 'https://token.actions.githubusercontent.com',
  clientIds: ['sts.amazonaws.com'],
});

const deployRole = new iam.Role(this, 'GithubDeployRole', {
  assumedBy: new iam.WebIdentityPrincipal(githubOidcProvider.openIdConnectProviderArn, {
    StringLike: {
      'token.actions.githubusercontent.com:sub': `repo:${GITHUB_ORG}/${GITHUB_REPO}:ref:refs/heads/main`,
    },
    StringEquals: {
      'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
    },
  }),
  managedPolicies: [iam.ManagedPolicy.fromAwsManagedPolicyName('PowerUserAccess')],
  description: 'Role assumed by GitHub Actions OIDC for CDK deployment',
});
```

**NEVER use `PowerUserAccess` in production** � scope it down to only the actions CDK needs.
For initial setup this is acceptable; update to least-privilege after first successful deploy.

### Step 3: Set GitHub Environment Variables
In the GitHub repository settings, create environments (dev, staging, prod) with these variables:
- `AWS_REGION` � e.g., `us-east-1`
- `DEV_DEPLOY_ROLE_ARN` � ARN of the OIDC deploy role for dev
- `STAGING_DEPLOY_ROLE_ARN` � ARN of the OIDC deploy role for staging
- `PROD_DEPLOY_ROLE_ARN` � ARN of the OIDC deploy role for prod

**Never store these as GitHub Secrets** � they are not sensitive. Use Variables (not Secrets).

### Step 4: Add npm Scripts to package.json
Verify these scripts exist in `package.json`:
```json
{
  "scripts": {
    "build": "tsc",
    "lint": "eslint 'src/**/*.ts'",
    "test": "jest",
    "test:integration": "jest --config jest.integration.config.ts",
    "cdk": "cdk"
  }
}
```

### Step 5: Validate Pipeline Configuration
Verify:
- [ ] No `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` anywhere in `.github/workflows/`
- [ ] `id-token: write` permission is set at the job or workflow level
- [ ] `contents: read` is the only other permission (principle of least privilege)
- [ ] Manual approval gate exists for the prod environment (configured in GitHub environment settings)

## OUTPUT CONTRACT

1. Write `.github/workflows/deploy.yml`
2. Update the infra CDK stack with the OIDC provider and deploy role constructs
3. Document the GitHub environment variable names in `.env.example`
4. Write this exact phrase to signal completion:
   `Pipeline configured. Activating environment_promotion.`
