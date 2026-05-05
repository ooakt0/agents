# 🤝 AGENT HANDOFF: [TASK_ID] - [TASK_NAME]

## 📋 METADATA
- **From:** @techLead
- **To:** @[TargetAgentName]
- **Priority:** [Low | Medium | High | Critical]
- **Status:** 🏗️ ACTIVE
- **Language / Stack:** [TypeScript | Python | Java | Kotlin | JavaScript | React | Next.js | Angular | N/A]
- **Change Type:** [New Feature | Change Request — UI | Change Request — Bug Fix | Change Request — API | Change Request — Backend | Change Request — Infrastructure | Change Request — Config]

---

## 🎯 OBJECTIVE
> [Clear, concise description of what needs to be achieved in this specific task.]

---

## 🏗️ TECHNICAL CONTEXT
- **Project State Reference:** See `.github/shared/project_state.md` Task [ID].
- **Architecture Decisions:** Refer to `.github/shared/architecture_log.md` ADR-[ID].
- **Relevant Files:** 
    - `[Path/to/file1]`
    - `[Path/to/file2]`

---

## 🛠️ SKILLS REQUIRED
Use the following skills defined in your agent folder:
1. `skill:[SkillName1].md`
2. `skill:[SkillName2].md`

---

## 🚧 CONSTRAINTS & STANDARDS
Refer to `.github/shared/standards.md` specifically for:
- [ ] **Section [X]:** [e.g., AWS IAM Least Privilege]
- [ ] **Section [Y]:** [e.g., TypeScript Naming Conventions]
- [ ] **Section [Z]:** [e.g., Unit Test Coverage > 80%]

---

## ✅ DEFINITION OF DONE (DoD)
The task is only complete when:
1. [ ] [Specific requirement 1, e.g., Lambda function is written in TS]
2. [ ] [Specific requirement 2, e.g., Unit tests pass with mock data]
3. [ ] [Specific requirement 3, e.g., `project_state.md` updated to ✅ DONE]

---

## 🛑 BLOCKER PROTOCOL
If you encounter a missing dependency, AWS permission error, or logic conflict:
1. Stop immediately.
2. Update `.github/shared/project_state.md` under **⚠️ BLOCKERS**.
3. Ping @techLead for resolution.
