-- Synthetic development data only; not real Laurier courses or employers.

set local search_path = vantage, pg_catalog;

insert into companies (id, name, slug, industry, careers_url) values ('fa0573dd-5afa-5262-a43e-3ce7b67f850e', 'Example North Analytics', 'demo-north', 'Synthetic demo', 'https://example.org/north/careers') on conflict do nothing;

insert into job_sources (id, company_id, source_type, base_url, adapter_key, enabled, is_synthetic, access_review_status) values ('31d33de5-65b5-5374-86fb-a4d9dbf7f4e7', 'fa0573dd-5afa-5262-a43e-3ce7b67f850e', 'custom_api', 'https://example.org/north', 'fixture-north', false, true, 'pending') on conflict do nothing;

insert into companies (id, name, slug, industry, careers_url) values ('c1aa5cd4-c35b-5353-8251-415cb40a1899', 'Example Maple Technology', 'demo-maple', 'Synthetic demo', 'https://example.org/maple/careers') on conflict do nothing;

insert into job_sources (id, company_id, source_type, base_url, adapter_key, enabled, is_synthetic, access_review_status) values ('48370c6e-df8a-589a-8617-579279185f85', 'c1aa5cd4-c35b-5353-8251-415cb40a1899', 'custom_api', 'https://example.org/maple', 'fixture-maple', false, true, 'pending') on conflict do nothing;

insert into job_roles (id, slug, name, category) values ('4b7631f9-edcb-5112-bdca-9a97e54a934e', 'data-analyst', 'Data Analyst', 'Synthetic demo') on conflict do nothing;

insert into job_roles (id, slug, name, category) values ('098f7593-ea64-5a11-81a8-c174179b9fb5', 'software-developer', 'Software Developer', 'Synthetic demo') on conflict do nothing;

insert into skills (id, slug, name, category) values ('41906085-5976-5840-9009-9c9e79a5f096', 'python', 'Python', 'Programming language') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('89a11862-b105-5ea0-bb56-89d7d2519fc4', '41906085-5976-5840-9009-9c9e79a5f096', 'Python', 'python') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('ce1ecd66-63f8-530b-9f56-72e73d171cd6', '41906085-5976-5840-9009-9c9e79a5f096', 'Python 3', 'python 3') on conflict do nothing;

insert into skills (id, slug, name, category) values ('3a5d3b78-0315-574c-8e61-7a60a4b7ad30', 'sql', 'SQL', 'Database') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('9b9d187b-11d7-51a4-82c1-6e3f1bf39cb7', '3a5d3b78-0315-574c-8e61-7a60a4b7ad30', 'SQL', 'sql') on conflict do nothing;

insert into skills (id, slug, name, category) values ('58aa65ab-d71c-5cd4-a0cb-a15f6fa5ef05', 'excel', 'Excel', 'Analytics software') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('f1f9b17d-dd36-50b7-87da-8da4fb6e1131', '58aa65ab-d71c-5cd4-a0cb-a15f6fa5ef05', 'Excel', 'excel') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('d63bc395-eca0-59a1-aa2a-e280ed45a49e', '58aa65ab-d71c-5cd4-a0cb-a15f6fa5ef05', 'Microsoft Excel', 'microsoft excel') on conflict do nothing;

insert into skills (id, slug, name, category) values ('c88d2934-aecc-5457-a57f-32a4827217e1', 'docker', 'Docker', 'Developer tool') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('173a344d-5409-5b86-b71c-eb8356f70c76', 'c88d2934-aecc-5457-a57f-32a4827217e1', 'Docker', 'docker') on conflict do nothing;

insert into skills (id, slug, name, category) values ('f99bdcf4-1765-5dc0-be6e-7e9a00bc503a', 'javascript', 'JavaScript', 'Programming language') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('db88dcfa-7256-5264-bff2-e6c44557ae43', 'f99bdcf4-1765-5dc0-be6e-7e9a00bc503a', 'JavaScript', 'javascript') on conflict do nothing;

insert into skill_aliases (id, skill_id, alias, normalized_alias) values ('ada8f242-c237-5370-961b-96102b5c9347', 'f99bdcf4-1765-5dc0-be6e-7e9a00bc503a', 'JS', 'js') on conflict do nothing;

insert into curriculum_sources (id, source_url, is_synthetic, source_type, catalog_year, title) values ('d301cc86-0657-5535-97b2-034de4999907', 'https://example.org/vantage/synthetic-curriculum', true, 'academic_calendar', '2026/27', 'Synthetic curriculum evidence — not a Laurier source') on conflict do nothing;

insert into programs (id, institution, name, slug, catalog_year, source_id, description) values ('5754e903-d1a6-54b1-8e4a-b50670c7f1d1', 'Synthetic demonstration institution', 'Synthetic Analytics Program', 'synthetic-analytics', '2026/27', 'd301cc86-0657-5535-97b2-034de4999907', 'Illustrative program for testing the curriculum-to-job workflow. This is not a real Laurier program.') on conflict do nothing;

insert into courses (id, code, title, catalog_year, description, source_id) values ('230d7108-b218-507e-af61-27ee24468e60', 'DEMO101', 'Data Foundations', '2026/27', 'Synthetic course for development only.', 'd301cc86-0657-5535-97b2-034de4999907') on conflict do nothing;

insert into program_courses (program_id, course_id, requirement_type, suggested_year) values ('5754e903-d1a6-54b1-8e4a-b50670c7f1d1', '230d7108-b218-507e-af61-27ee24468e60', 'required', 1) on conflict do nothing;

insert into courses (id, code, title, catalog_year, description, source_id) values ('6f763e70-146e-508b-96cc-fda9da5c745b', 'DEMO102', 'Analytical Practice', '2026/27', 'Synthetic course for development only.', 'd301cc86-0657-5535-97b2-034de4999907') on conflict do nothing;

insert into program_courses (program_id, course_id, requirement_type, suggested_year) values ('5754e903-d1a6-54b1-8e4a-b50670c7f1d1', '6f763e70-146e-508b-96cc-fda9da5c745b', 'required', 1) on conflict do nothing;

insert into courses (id, code, title, catalog_year, description, source_id) values ('895e4dcf-86da-5fb2-8a4a-09c0799c11c1', 'DEMO201', 'Application Projects', '2026/27', 'Synthetic course for development only.', 'd301cc86-0657-5535-97b2-034de4999907') on conflict do nothing;

insert into program_courses (program_id, course_id, requirement_type, suggested_year) values ('5754e903-d1a6-54b1-8e4a-b50670c7f1d1', '895e4dcf-86da-5fb2-8a4a-09c0799c11c1', 'elective', 1) on conflict do nothing;

insert into course_skills (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url, verification_status, extraction_method, verified_at) values ('230d7108-b218-507e-af61-27ee24468e60', '41906085-5976-5840-9009-9c9e79a5f096', 'practiced', 'Synthetic example: DEMO101 includes Python at practiced coverage. Not real curriculum evidence.', 'https://example.org/vantage/synthetic-curriculum', 'verified', 'manual', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into course_skills (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url, verification_status, extraction_method, verified_at) values ('230d7108-b218-507e-af61-27ee24468e60', '3a5d3b78-0315-574c-8e61-7a60a4b7ad30', 'assessed', 'Synthetic example: DEMO101 includes SQL at assessed coverage. Not real curriculum evidence.', 'https://example.org/vantage/synthetic-curriculum', 'verified', 'manual', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into course_skills (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url, verification_status, extraction_method, verified_at) values ('6f763e70-146e-508b-96cc-fda9da5c745b', '58aa65ab-d71c-5cd4-a0cb-a15f6fa5ef05', 'introduced', 'Synthetic example: DEMO102 includes Excel at introduced coverage. Not real curriculum evidence.', 'https://example.org/vantage/synthetic-curriculum', 'verified', 'manual', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into course_skills (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url, verification_status, extraction_method, verified_at) values ('6f763e70-146e-508b-96cc-fda9da5c745b', 'c88d2934-aecc-5457-a57f-32a4827217e1', 'mentioned', 'Synthetic example: DEMO102 includes Docker at mentioned coverage. Not real curriculum evidence.', 'https://example.org/vantage/synthetic-curriculum', 'pending', 'manual', null) on conflict do nothing;

insert into course_skills (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url, verification_status, extraction_method, verified_at) values ('895e4dcf-86da-5fb2-8a4a-09c0799c11c1', 'c88d2934-aecc-5457-a57f-32a4827217e1', 'assessed', 'Synthetic example: DEMO201 includes Docker at assessed coverage. Not real curriculum evidence.', 'https://example.org/vantage/synthetic-curriculum', 'verified', 'manual', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into course_skills (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url, verification_status, extraction_method, verified_at) values ('895e4dcf-86da-5fb2-8a4a-09c0799c11c1', 'f99bdcf4-1765-5dc0-be6e-7e9a00bc503a', 'assessed', 'Synthetic example: DEMO201 includes JavaScript at assessed coverage. Not real curriculum evidence.', 'https://example.org/vantage/synthetic-curriculum', 'verified', 'manual', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into program_roles (program_id, role_id, relevance, rationale) values ('5754e903-d1a6-54b1-8e4a-b50670c7f1d1', '4b7631f9-edcb-5112-bdca-9a97e54a934e', 'related', 'Synthetic demo relationship') on conflict do nothing;

insert into program_roles (program_id, role_id, relevance, rationale) values ('5754e903-d1a6-54b1-8e4a-b50670c7f1d1', '098f7593-ea64-5a11-81a8-c174179b9fb5', 'related', 'Synthetic demo relationship') on conflict do nothing;

insert into jobs (id, source_id, company_id, source_key, external_id, title, description_text, source_url, apply_url, role_id, employment_type, work_mode, location_raw, city, province, country, salary_min, salary_max, salary_currency, salary_period, first_seen_at, last_seen_at) values ('26ddc9ff-7a89-52e1-8f92-e04d565aca78', '31d33de5-65b5-5374-86fb-a4d9dbf7f4e7', 'fa0573dd-5afa-5262-a43e-3ce7b67f850e', 'analyst-intern', 'analyst-intern', 'Data Analyst Intern', 'Synthetic demonstration posting. SQL is required. Python is required. Excel is preferred. This is not a real job opening.', 'https://example.org/north/jobs/analyst-intern', 'https://example.org/north/jobs/analyst-intern', '4b7631f9-edcb-5112-bdca-9a97e54a934e', 'internship', 'hybrid', 'Toronto, ON, Canada', 'Toronto', 'Ontario', 'Canada', 28, 35, 'CAD', 'hour', '2026-10-21T12:00:00Z', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('26ddc9ff-7a89-52e1-8f92-e04d565aca78', '3a5d3b78-0315-574c-8e61-7a60a4b7ad30', 'required', 1, 'Synthetic posting: SQL is required.', 'fixture-v1') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('26ddc9ff-7a89-52e1-8f92-e04d565aca78', '41906085-5976-5840-9009-9c9e79a5f096', 'required', 1, 'Synthetic posting: Python is required.', 'fixture-v1') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('26ddc9ff-7a89-52e1-8f92-e04d565aca78', '58aa65ab-d71c-5cd4-a0cb-a15f6fa5ef05', 'preferred', 1, 'Synthetic posting: Excel is preferred.', 'fixture-v1') on conflict do nothing;

insert into jobs (id, source_id, company_id, source_key, external_id, title, description_text, source_url, apply_url, role_id, employment_type, work_mode, location_raw, city, province, country, salary_min, salary_max, salary_currency, salary_period, first_seen_at, last_seen_at) values ('8ee24e20-193c-5cd6-8efe-e086f10c056a', '31d33de5-65b5-5374-86fb-a4d9dbf7f4e7', 'fa0573dd-5afa-5262-a43e-3ce7b67f850e', 'reporting-analyst', 'reporting-analyst', 'Junior Reporting Analyst', 'Synthetic demonstration posting. SQL is required. Excel is required. This is not a real job opening.', 'https://example.org/north/jobs/reporting-analyst', 'https://example.org/north/jobs/reporting-analyst', '4b7631f9-edcb-5112-bdca-9a97e54a934e', 'new_grad', 'onsite', 'Waterloo, ON, Canada', 'Waterloo', 'Ontario', 'Canada', 60000, 75000, 'CAD', 'year', '2026-10-21T12:00:00Z', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('8ee24e20-193c-5cd6-8efe-e086f10c056a', '3a5d3b78-0315-574c-8e61-7a60a4b7ad30', 'required', 1, 'Synthetic posting: SQL is required.', 'fixture-v1') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('8ee24e20-193c-5cd6-8efe-e086f10c056a', '58aa65ab-d71c-5cd4-a0cb-a15f6fa5ef05', 'required', 1, 'Synthetic posting: Excel is required.', 'fixture-v1') on conflict do nothing;

insert into jobs (id, source_id, company_id, source_key, external_id, title, description_text, source_url, apply_url, role_id, employment_type, work_mode, location_raw, city, province, country, salary_min, salary_max, salary_currency, salary_period, first_seen_at, last_seen_at) values ('5604a1c3-8989-59c2-b4f2-981d8fc04fa4', '48370c6e-df8a-589a-8617-579279185f85', 'c1aa5cd4-c35b-5353-8251-415cb40a1899', 'developer-intern', 'developer-intern', 'Software Developer Co-op', 'Synthetic demonstration posting. Python is required. Docker is preferred. JavaScript is mentioned. This is not a real job opening.', 'https://example.org/maple/jobs/developer-intern', 'https://example.org/maple/jobs/developer-intern', '098f7593-ea64-5a11-81a8-c174179b9fb5', 'co_op', 'remote', 'Ottawa, ON, Canada', 'Ottawa', 'Ontario', 'Canada', null, null, null, null, '2026-10-21T12:00:00Z', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('5604a1c3-8989-59c2-b4f2-981d8fc04fa4', '41906085-5976-5840-9009-9c9e79a5f096', 'required', 1, 'Synthetic posting: Python is required.', 'fixture-v1') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('5604a1c3-8989-59c2-b4f2-981d8fc04fa4', 'c88d2934-aecc-5457-a57f-32a4827217e1', 'preferred', 1, 'Synthetic posting: Docker is preferred.', 'fixture-v1') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('5604a1c3-8989-59c2-b4f2-981d8fc04fa4', 'f99bdcf4-1765-5dc0-be6e-7e9a00bc503a', 'mentioned', 1, 'Synthetic posting: JavaScript is mentioned.', 'fixture-v1') on conflict do nothing;

insert into jobs (id, source_id, company_id, source_key, external_id, title, description_text, source_url, apply_url, role_id, employment_type, work_mode, location_raw, city, province, country, salary_min, salary_max, salary_currency, salary_period, first_seen_at, last_seen_at) values ('99958f89-3dc5-554d-b225-de255c5d612b', '48370c6e-df8a-589a-8617-579279185f85', 'c1aa5cd4-c35b-5353-8251-415cb40a1899', 'graduate-developer', 'graduate-developer', 'Graduate Application Developer', 'Synthetic demonstration posting. JavaScript is required. SQL is preferred. This is not a real job opening.', 'https://example.org/maple/jobs/graduate-developer', 'https://example.org/maple/jobs/graduate-developer', '098f7593-ea64-5a11-81a8-c174179b9fb5', 'new_grad', 'hybrid', 'Toronto, ON, Canada', 'Toronto', 'Ontario', 'Canada', null, null, null, null, '2026-10-21T12:00:00Z', '2026-10-21T12:00:00Z') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('99958f89-3dc5-554d-b225-de255c5d612b', 'f99bdcf4-1765-5dc0-be6e-7e9a00bc503a', 'required', 1, 'Synthetic posting: JavaScript is required.', 'fixture-v1') on conflict do nothing;

insert into job_skills (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version) values ('99958f89-3dc5-554d-b225-de255c5d612b', '3a5d3b78-0315-574c-8e61-7a60a4b7ad30', 'preferred', 1, 'Synthetic posting: SQL is preferred.', 'fixture-v1') on conflict do nothing;
