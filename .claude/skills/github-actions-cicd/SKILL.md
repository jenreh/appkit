---
name: github-actions-cicd
description: 'Create, audit, or troubleshoot GitHub Actions CI/CD pipelines. Use when: building a new workflow, reviewing an existing pipeline for security/performance, debugging a failing workflow, designing deployment strategies, or setting up secrets/OIDC authentication. Triggers: "create workflow", "CI/CD pipeline", "GitHub Actions", "review pipeline", "audit workflow", "fix workflow", "deployment strategy", "OIDC", "caching", "matrix strategy".'
argument-hint: 'create | review | troubleshoot'
---

# GitHub Actions CI/CD Skill

## When to Use
- Creating a new CI/CD workflow from scratch
- Auditing an existing workflow for security, performance, or correctness
- Debugging a failing or misbehaving workflow
- Designing deployment strategies (rolling, blue/green, canary)
- Configuring secrets, OIDC, or environment protections

---

## Mode: Create

### 1. Gather Requirements
Ask (or infer from context):
- Trigger events: `push`, `pull_request`, `workflow_dispatch`, `schedule`?
- Language/runtime (Python, Node.js, etc.) — determines setup actions and cache paths
- Test stages needed: unit, integration, E2E?
- Deployment target: cloud provider, registry, k8s?
- Environments: staging + production with manual approval gates?

### 2. Scaffold Structure
```
name: <Descriptive Name>
on: ...
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read  # least privilege default
jobs:
  lint:   ...
  test:   ...
  build:  ...
  deploy: ...
```

### 3. Apply Checklist per Job
- [ ] `runs-on: ubuntu-latest` (or justified alternative)
- [ ] `actions/checkout@v4` with `fetch-depth: 1`
- [ ] Cache keyed on `hashFiles('**/lockfile')` with `restore-keys` fallback
- [ ] All `uses:` pinned to full commit SHA or major version tag (`@v4`, not `@main`)
- [ ] `timeout-minutes` set for long-running jobs
- [ ] Secrets via `${{ secrets.NAME }}` — never hardcoded

### 4. Security Gates
- Least-privilege `permissions` block at workflow + override at job level
- OIDC for cloud auth (prefer over long-lived keys)
- `dependency-review-action` on PRs targeting default branch
- CodeQL or Bandit for SAST on push/PR

### 5. Deployment Configuration
- Use `environment:` blocks with protection rules for staging/prod
- Manual approval required for `production` environment
- Store rollback artifact version as job output; document rollback command in workflow comment

---

## Mode: Review (Audit Checklist)

Run through these checks on any existing workflow:

### Structure
- [ ] Workflow `name` is descriptive
- [ ] `concurrency` prevents redundant runs
- [ ] `permissions` explicitly scoped (not default write-all)

### Security
- [ ] No hardcoded credentials — all via `secrets.*`
- [ ] OIDC used for AWS/Azure/GCP (not static keys)
- [ ] Action versions pinned (`@v4` or SHA, not `@latest`/`@main`)
- [ ] `dependency-review-action` present on PRs
- [ ] SAST tool integrated and blocking on critical findings

### Performance
- [ ] `fetch-depth: 1` on checkout
- [ ] Cache configured with `hashFiles`-based key + `restore-keys`
- [ ] Matrix strategy used where parallelism applies
- [ ] Large artifacts uploaded/downloaded; not rebuilt per job

### Testing
- [ ] Unit tests run early; integration tests after
- [ ] Test reports published as artifacts or GitHub Checks
- [ ] Coverage threshold enforced

### Deployment
- [ ] Staging deploys before production
- [ ] Manual approval gate on production environment
- [ ] Rollback strategy documented or automated
- [ ] Post-deploy health checks / smoke tests present

---

## Mode: Troubleshoot

### Workflow not triggering?
1. Check `on:` trigger matches the actual event
2. Verify `branches:`/`paths:` filters — are they too narrow?
3. Check `concurrency` group — is a prior run blocking?
4. Look for required status checks blocking the workflow on branch protection

### Permission denied / 403?
1. Inspect `permissions:` block — add the specific scope needed
2. For environment secrets: check if manual approval is pending
3. For OIDC: verify trust policy in cloud provider matches `github.repository` / `github.ref`

### Cache miss every run?
1. Print the computed cache key in a `run:` step to debug
2. Verify `path:` matches where the package manager actually installs
3. Check if lockfile path in `hashFiles()` is correct (use `**` for monorepos)

### Flaky tests in CI?
1. Add explicit waits; remove `sleep`
2. Use `services:` containers instead of external services
3. Set `fail-fast: false` in matrix to see all failures
4. Capture screenshots/video on failure for E2E tests

### Slow workflow?
1. Profile step durations in the Actions run summary
2. Add/fix caching (check hit rate in logs)
3. Parallelise with `strategy.matrix`
4. Move non-blocking steps (docs, badges) to separate scheduled workflow

---

## Reference: Common Patterns

### OIDC for AWS
```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/my-role
      aws-region: eu-west-1
```

### Effective Cache Key (Python/uv)
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml', '**/uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-uv-
```

### Production Environment with Approval
```yaml
deploy-prod:
  needs: deploy-staging
  environment:
    name: production
    url: https://example.com
  if: github.ref == 'refs/heads/main'
```

### Dependency Review on PRs
```yaml
- uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: high
```
