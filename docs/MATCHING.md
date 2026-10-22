# Experimental curriculum alignment

The API uses `heuristic-v1-experimental`. It describes **documented coursework overlap**, not personal proficiency, eligibility, or hiring probability. The current demonstration data is invented; no real curriculum assertions have been verified.

1. Select the program's academic-year records.
2. Include only verified introduced/practiced/assessed skill evidence from compulsory courses. Exclude electives, concentrations, choice groups, pending/rejected claims, and mentioned-only coverage.
3. Weight extracted job requirements: required = 3, preferred = 1.5, mentioned = 1, each multiplied by extraction confidence.
4. For each matching skill, choose the strongest documented course coverage: introduced = 0.35, practiced = 0.70, assessed = 1. Multiple courses do not multiply coverage.
5. Divide the sum of weighted covered requirements by total weighted extracted requirements and multiply by 100. Round to one decimal place.

When there are no positive-confidence job skills or no eligible curriculum evidence, return `alignment_percent: null` and `status: insufficient_evidence`. A genuine evaluated set with evidence but no overlap can score zero. Responses retain matched skills, supporting courses/excerpts/URLs, unmatched requirements, method version, and caveat.

The synthetic Data Analyst Intern demonstrates the calculation: required SQL at assessed coverage contributes 3; required Python at practiced coverage contributes 2.1; preferred Excel at introduced coverage contributes 0.525. Divide 5.625 by 7.5 to obtain **75%**. Docker's elective coverage and pending compulsory-course mention do not enter default matching.

Before promoting numeric scores for real data, evaluate manually reviewed program–job pairs, skill extraction precision/recall, and ranking quality. The baseline endpoint explains an individual job against a selected program; relevance ranking across role families is deferred.
