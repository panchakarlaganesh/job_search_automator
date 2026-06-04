---
name: resume-mastery
description: Advanced high-fidelity resume tailoring and ATS optimization for senior SRE/DevOps roles. Use when you need to perform deep optimization including keyword gap analysis, skill mapping, and impact quantification for specific job applications.
---

# Resume Mastery

## Overview

This skill enables a high-end "Grads.jobs" style tailoring for senior technical resumes. It goes beyond simple editing by performing a keyword gap analysis and dynamically restructuring skills and experience to maximize ATS matching.

## Advanced ATS Optimization Workflow

### 1. Keyword Gap Analysis (JD vs. Resume)
- **Identify 'Hard' Keywords:** Extract mandatory technical tools (e.g., "Terraform", "Linkerd", "Boto3").
- **Identify 'Soft' Keywords:** Extract methodologies and frameworks (e.g., "Post-mortems", "Error Budgets", "SOC2 Compliance").
- **Gap Map:** List keywords present in the JD but missing from the current resume.

### 2. Strategic Skill Mapping
- **Primary Focus:** The 'Technical Skills' section must be re-ordered to put the most relevant JD keywords at the very beginning of each category.
- **Title Alignment:** If the JD uses a specific variation of your title (e.g., "Cloud Reliability Engineer"), ensure this exact phrase is used in the summary/header.

### 3. Surgical Role Optimization (The "Grads.jobs" Method)
- **Bullet Prioritization:** For each role in your history, move bullets that use JD technologies to the top of that role's list.
- **Impact Injection:** Every bullet point must follow the **[Action Verb] + [Task] + [Quantifiable Result]** formula.
  - *Example:* "Optimized SQL queries" -> "Optimized SQL performance by analyzing Explain Plans, resolving back-end bottlenecks and improving query speed by 25%."
- **Keyword Weaving:** Naturally replace general terms with the specific terms from the JD (e.g., change "monitoring" to "Observability with Datadog" if that's what they use).

## High-Fidelity Rendering Rules

- **Format:** Single-column, clean layout using standard headers.
- **Template:** Use `assets/resume_template.html`.
- **Fidelity:** NEVER remove core architectural experience; only enhance the "flavor" of the experience to match the employer's needs.

## Usage Guidelines

1. **Analysis:** Run a keyword comparison first.
2. **Drafting:** Update the Markdown content using the "Role Optimization" rules.
3. **Review:** Ensure NO new skills were invented—only emphasis changed.
4. **Export:** Generate PDF via `pdf-mcp-server`.

## Resources

### assets/resume_template.html
ATS-standard professional template.

### references/ats_keywords.md
Standardized SRE/DevOps keyword bank.
