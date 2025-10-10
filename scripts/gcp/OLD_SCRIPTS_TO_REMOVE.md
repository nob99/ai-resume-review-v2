# Old Scripts to Remove After Validation

**Status:** ⏳ Pending Removal (awaiting validation period)
**Created:** 2025-10-10
**Remove After:** 2025-11-10 (4 weeks validation period)

---

## ⚠️ **DO NOT REMOVE YET**

These scripts must remain until:
1. ✅ New scripts tested in production
2. ✅ All team members notified
3. ✅ CI/CD pipelines updated
4. ✅ 4-week validation period complete

---

## 📋 Files to Remove

### Monitoring Scripts (7 files)

```bash
scripts/gcp/monitoring/1-setup-notification-channels.sh
scripts/gcp/monitoring/2-setup-uptime-checks.sh
scripts/gcp/monitoring/3-setup-critical-alerts.sh
scripts/gcp/monitoring/4-setup-log-metrics.sh
scripts/gcp/monitoring/5-setup-budget-alert.sh
scripts/gcp/monitoring/run-all-setup.sh
scripts/gcp/monitoring/verify-setup.sh
```

**Replaced by:**
- `scripts/gcp/monitoring/setup.sh`
- `scripts/gcp/monitoring/verify.sh`

---

### Deployment Scripts (5 files)

```bash
scripts/gcp/deploy/1-verify-prerequisites.sh
scripts/gcp/deploy/2-run-migrations.sh
scripts/gcp/deploy/3-deploy-backend.sh
scripts/gcp/deploy/4-deploy-frontend.sh
scripts/gcp/deploy/deploy-all.sh
```

**Replaced by:**
- `scripts/gcp/deploy/deploy.sh`

---

### Setup Scripts (4 files)

```bash
scripts/gcp/setup/setup-gcp-project.sh
scripts/gcp/setup/setup-cloud-sql.sh
scripts/gcp/setup/setup-secrets.sh
scripts/gcp/setup/cleanup-old-resources.sh
```

**Replaced by:**
- `scripts/gcp/setup/setup.sh`
- `scripts/gcp/setup/cleanup.sh`

---

## 📊 Summary

**Total files to remove:** 16 files
**Total new files:** 5 files
**Net reduction:** 11 files (52% fewer files after cleanup)

---

## ✅ Validation Checklist

Before removing these files, ensure:

### Testing
- [ ] Test `monitoring/setup.sh` in production
- [ ] Test `deploy/deploy.sh` in production
- [ ] Test `setup/setup.sh` on test GCP project
- [ ] Verify all --dry-run modes work correctly
- [ ] Verify all --step modes work correctly
- [ ] Test error handling and rollback

### Communication
- [ ] Notify all team members of new scripts
- [ ] Share migration guide (scripts/gcp/README.md)
- [ ] Update team documentation/wiki
- [ ] Announce deprecation timeline

### Infrastructure
- [ ] Check GitHub Actions workflows for old script references
- [ ] Update CI/CD pipelines to use new scripts
- [ ] Update any deployment runbooks
- [ ] Update any monitoring dashboards/links

### Documentation
- [ ] Verify all README files are updated
- [ ] Ensure migration path is clear
- [ ] Add deprecation warnings to old scripts (optional)

### Final Verification
- [ ] Confirm no usage of old scripts in codebase
- [ ] Grep for old script names in all files
- [ ] Verify new scripts have been used successfully
- [ ] Get approval from team lead

---

## 🗑️ Removal Commands

**When ready to remove (after all checks complete):**

```bash
# Remove old monitoring scripts
rm scripts/gcp/monitoring/1-setup-notification-channels.sh
rm scripts/gcp/monitoring/2-setup-uptime-checks.sh
rm scripts/gcp/monitoring/3-setup-critical-alerts.sh
rm scripts/gcp/monitoring/4-setup-log-metrics.sh
rm scripts/gcp/monitoring/5-setup-budget-alert.sh
rm scripts/gcp/monitoring/run-all-setup.sh
rm scripts/gcp/monitoring/verify-setup.sh

# Remove old deployment scripts
rm scripts/gcp/deploy/1-verify-prerequisites.sh
rm scripts/gcp/deploy/2-run-migrations.sh
rm scripts/gcp/deploy/3-deploy-backend.sh
rm scripts/gcp/deploy/4-deploy-frontend.sh
rm scripts/gcp/deploy/deploy-all.sh

# Remove old setup scripts
rm scripts/gcp/setup/setup-gcp-project.sh
rm scripts/gcp/setup/setup-cloud-sql.sh
rm scripts/gcp/setup/setup-secrets.sh
rm scripts/gcp/setup/cleanup-old-resources.sh

# Commit the cleanup
git add -A
git commit -m "chore: remove deprecated GCP scripts after validation period

Remove old scripts that have been replaced by consolidated versions.
All functionality has been tested and validated in production.

Removed 16 deprecated scripts:
- Monitoring: 7 scripts → 2 scripts
- Deployment: 5 scripts → 1 script
- Setup: 4 scripts → 2 scripts

See scripts/gcp/REFACTORING_COMPLETE.md for details.
"
```

---

## 📅 Timeline

| Date | Action | Status |
|------|--------|--------|
| 2025-10-10 | New scripts created and committed | ✅ Complete |
| 2025-10-10 | Documentation updated | ✅ Complete |
| 2025-10-10 | Old scripts marked for removal | ✅ Complete |
| 2025-10-17 | Add deprecation warnings (optional) | ⏳ Pending |
| 2025-10-24 | Test new scripts in production | ⏳ Pending |
| 2025-11-07 | Final validation complete | ⏳ Pending |
| 2025-11-10 | Remove old scripts | ⏳ Pending |

---

## 🔍 How to Check for Old Script Usage

```bash
# Check for references to old scripts in codebase
cd /path/to/ai-resume-review-v2

# Search for old monitoring scripts
grep -r "1-setup-notification-channels" --exclude-dir=.git

# Search for old deployment scripts
grep -r "deploy-all.sh" --exclude-dir=.git
grep -r "3-deploy-backend" --exclude-dir=.git

# Search for old setup scripts
grep -r "setup-gcp-project.sh" --exclude-dir=.git
grep -r "setup-cloud-sql.sh" --exclude-dir=.git

# If no results, safe to remove!
```

---

## ⚠️ Important Notes

1. **Keep this file** until old scripts are removed
2. **Update status** as validation progresses
3. **Don't rush** - validation period is important
4. **Test thoroughly** before removing
5. **Communicate clearly** with team

---

**Last Updated:** 2025-10-10
**Next Review:** 2025-10-24 (2 weeks)
**Scheduled Removal:** 2025-11-10 (4 weeks)
