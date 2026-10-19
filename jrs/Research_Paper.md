# AI Powered Job Recommendation and Career Intelligence System
## A prototype for resume analysis, job matching, and skill gap guidance

**Student:** ______________________________  
**Programme:** Bachelor of Computer Applications  
**Institution:** ______________________________  
**Project guide:** ______________________________  
**Academic year:** 2026–2027

## Abstract

Online job search can require candidates to compare many job descriptions with their own skills, education, interests, and location preferences. This project presents a web-based career intelligence prototype that brings profile management, job recommendations, résumé text analysis, skill gap guidance, learning goals, interview practice, and application tracking into one system. The prototype uses Flask and SQLite. Its recommendation score combines required-skill overlap, role-interest alignment, pairwise lexical similarity, location preference, experience level, and employment type. A user can inspect the match score, matched skills, and missing listed skills instead of receiving an unexplained ranking. The system also supports consent-based text extraction from selectable PDF résumés, profile-based skill suggestions, rule-based résumé checks, saved jobs, skill evidence, and administrative job-data import.

The current project is an educational prototype with a small seeded demonstration dataset. Its text similarity is a lightweight pairwise TF-IDF-style cosine signal, not a trained semantic model. The sample listings are not live vacancies, and the prototype has not yet been evaluated with a labeled job-seeker dataset. This paper therefore describes the system design and proposes an evaluation using relevance judgments, ranking metrics, functional testing, and user feedback. It reports no measured recommendation accuracy. The system is intended to support job seekers' decisions; it does not determine employability or guarantee a hiring outcome.

**Keywords:** job recommendation, content-based filtering, TF-IDF, cosine similarity, résumé parsing, skill gap analysis, career planning

## 1. Introduction

Job seekers encounter listings that vary in terminology, required qualifications, experience levels, work arrangements, and location. A candidate may know their own skills but still need to compare them against multiple descriptions and decide which opportunities are worth pursuing. A search interface can retrieve listings containing a query term, but keyword search alone does not explain how a role relates to a candidate's profile or what listed requirements may be missing.

Job recommendation research has explored content-based filtering, collaborative filtering, and hybrid approaches. Content-based methods compare user and job attributes or text. They are useful when a new user has no interaction history, although their results depend on profile quality, job data, and the way text is represented [1], [2]. Résumé parsing presents a related challenge because résumés use varied layouts and section names; extracting structured information reliably is not a trivial keyword lookup [3].

This project focuses on a practical first version for students, fresh graduates, experienced job seekers, and career changers. It connects job search with profile editing, résumé skill organization, explainable match details, skill gap review, learning plans, practice activities, and application tracking. Its purpose is to help a user understand the available evidence and choose their next action. It does not make employment decisions.

## 2. Problem Statement

Many job seekers must manually compare their qualifications and preferences with a growing set of job advertisements. This makes it harder to identify relevant openings, see which listed skills they already possess, and decide what to learn next. A basic keyword search returns text matches but does not necessarily give a personalized explanation. A recommendation score without an explanation can also be difficult for a user to assess.

The project addresses the following question: **How can a small web application combine a candidate profile and job attributes to rank sample jobs, explain the main match factors, and turn missing listed skills into practical next steps?** The question is limited to a prototype and a controlled job dataset. It does not claim to solve the broader hiring or labor-market matching problem.

## 3. Aim and Objectives

The aim is to design and implement a web-based job recommendation and career support prototype that makes profile-to-job comparisons understandable and actionable.

The objectives are to:

1. Provide account registration, login, profile editing, and account deletion.
2. Store education, experience, skills, career goals, and job preferences in a structured profile.
3. Accept a user-consented, text-based PDF résumé and extract text for review.
4. Rank available jobs using skill overlap and profile/job text similarity alongside preference factors.
5. Explain the score using matched skills, missing listed skills, and profile factors.
6. Provide a skill gap view, learning plan, career action plan, and job application tracker.
7. Support transparent limitations, user review, privacy controls, and administrative management of the local job dataset.

## 4. Scope

The prototype includes a Flask web server, Jinja templates, CSS and JavaScript, and a SQLite database. The implemented features include user accounts with hashed passwords, a career profile, a small sample job dataset, job search and ranking, saved jobs, relevance feedback, PDF text extraction using `pypdf`, résumé skill suggestions, basic ATS-style checks, résumé text versions, skill evidence records, learning goals, interview practice prompts, a cover letter draft based on user-supplied evidence, an application tracker, saved search alerts, a rules-based career assistant, job risk phrase flags, and admin job management with CSV import.

The current prototype does not connect to a live job board, background alert delivery, external generative AI, OCR for scanned résumés, speech recognition, live labor-market data, or authoritative immigration information. The initial listings are demonstration records with placeholder links. These features require additional datasets, services, consent design, and evaluation before they can be presented as live services.

## 5. Literature Review

Fitria, Zaman, and Yaqin describe a content-based job recommendation approach using text preprocessing, TF-IDF weighting, and cosine similarity. Their study reports a dataset of 437 job advertisements and 100 user profiles, and reports average precision of 0.53 for its evaluation [1]. That result belongs to their dataset and evaluation method; it cannot be transferred to this project. The study provides a relevant model for comparing profile and vacancy text, while also emphasizing the need for actual data and relevance judgments.

Kumar et al. present a technical job recommendation system that uses APIs and web crawling to collect vacancy data and compares content-based and hybrid recommendation approaches [2]. This work highlights data acquisition and preprocessing as important system components. The current project instead starts with a small local dataset and offers administrative CSV import, allowing the recommendation workflow to be demonstrated without representing a crawler or live feed as implemented.

Barducci et al. study information extraction from Italian résumés. Their framework segments résumé text into semantically consistent portions and then applies named entity recognition to identify information such as skills and work experience [3]. Their work illustrates the difficulty of extracting structured data from heterogeneous résumé formats. The present prototype uses PDF text extraction and section-heading and skill-term heuristics. It therefore offers a simpler, reviewable feature and should not be treated as equivalent to a trained résumé parser.

Pedregosa et al. describe scikit-learn as a general-purpose machine-learning library for Python [4]. The broader value of such tools is reproducible text processing and model evaluation. The current prototype does not depend on scikit-learn; its text similarity function is implemented locally and uses a pairwise TF-IDF-style weighting. A future experimental version should use a corpus-fitted vectorizer and a fixed evaluation dataset so that its feature weights and rankings can be reproduced.

Responsible system design matters because recommendation outputs can influence a person's job search. NIST's AI Risk Management Framework identifies characteristics such as validity, reliability, accountability, transparency, explainability, privacy enhancement, and fairness as relevant trustworthiness concerns [5]. In this project, users can inspect the score components, update their profile, provide relevance feedback, and delete their account. Those controls are useful design steps, but they do not constitute a fairness audit or prove that the recommendations are valid.

## 6. Proposed System

### 6.1 System architecture

The application uses a browser-based user interface connected to Flask routes. Routes validate requests and apply account or administrator access checks. Recommendation and résumé-processing functions handle local analysis. SQLite stores user accounts, profiles, jobs, saved jobs, applications, learning records, practice records, skill evidence, alerts, and reports. Uploaded résumés are stored in a local upload directory and are associated with the account that submitted them.

The high-level process is:

**Candidate profile and résumé → normalized profile fields → job filtering and scoring → ranked job list with explanations → skill gaps and career actions → feedback and profile updates.**

### 6.2 User profile and résumé processing

The profile records the candidate's education, experience, technical and soft skills, interests, preferred roles, preferred location, employment type, experience level, and career goal. Comma-separated skills are normalized and duplicates are removed. PDF upload requires an explicit consent checkbox. The application extracts selectable text from the PDF and searches for a built-in set of skill terms and common section headings. The user is asked to review suggestions before adding them to a profile. Scanned image PDFs are not processed because OCR is not included.

### 6.3 Recommendation method

For each available listing, the prototype calculates a score from six factors:

| Factor | Weight | Prototype interpretation |
|---|---:|---|
| Required skill overlap | 45% | Fraction of listed job skills also present in the candidate profile |
| Text similarity | 15% | Pairwise TF-IDF-style cosine similarity between profile direction text and job text |
| Role alignment | 15% | Rule-based overlap between job title and interests, goals, and preferred roles |
| Location | 12% | Preference match, including remote listing handling |
| Experience | 8% | Agreement between profile and listing experience levels |
| Employment type | 5% | Agreement with the preferred work type, or neutral preference |

The weighted score is represented as a percentage from 0 to 100. The system then sorts jobs in descending score order. It separately reports exact skill terms found in the profile and required skill terms not found. These are text matches, not verification of competence. The score is a ranking aid and must not be interpreted as a probability of interview, selection, or job performance.

The current cosine implementation compares the two documents using a simple pairwise term-frequency and inverse-frequency calculation. It is not a learned semantic model and can miss synonyms, abbreviations, and context. A future version should define a stable vocabulary, fit IDF values over a declared corpus, normalize job and profile terms, and compare the baseline against alternatives.

### 6.4 Career support modules

The skill gap page compares the candidate profile against the selected job's listed skills and suggests a sequence: learn core concepts, complete a small project, and document evidence. Learning items can be marked complete. The career plan presents stages for building foundations, addressing gaps, showing evidence, and applying. Interview practice stores candidate responses and gives structure-focused feedback. A cover-letter helper requires the user to provide a genuine example before drafting. These modules are rule-based and do not verify knowledge or generate a validated career forecast.

## 7. Implementation Details

The software stack is Python, Flask, SQLite, HTML, CSS, and JavaScript. Passwords are stored as hashes using Werkzeug's password utilities. SQL statements use bound parameters. Account-owned records reference user identifiers and are removed through foreign-key cascades. POST requests use a session token check. Administrator-only routes support job creation and deletion, dataset import, category labels, and summary counts.

The application starts with ten demonstration jobs if the database is empty. Admin users can import CSV job records. The database can therefore be expanded for a controlled evaluation, but administrators must verify listing accuracy, permission to use the data, and the safety of application URLs before treating imported listings as current opportunities.

## 8. Evaluation Plan

No formal evaluation results are reported in this paper. A future evaluation should first create a consented, labeled dataset with representative candidate profiles and job listings. At least two reviewers should judge whether a job is relevant to a profile using predefined criteria. Disagreements should be recorded and resolved using a documented process.

The recommendation ranking can be evaluated with Precision@K, Recall@K, Mean Average Precision, and nDCG@K. These measures require relevance labels and should be reported with the dataset size and split method. A baseline keyword search and a skills-only weighted ranker should be compared with the combined score. Ablation tests should remove one score component at a time to estimate its effect. Profile variations should be reviewed for unequal outcomes across relevant candidate groups, while avoiding sensitive attributes unless their use has ethical and legal justification.

Functional evaluation should cover registration, authentication, profile update, consent enforcement, PDF upload and deletion, job search, score explanation, saved jobs, application updates, learning records, CSV import, and role-based access. Usability evaluation can ask participants to complete representative tasks and rate clarity, usefulness, and confidence in understanding recommendations. Resume extraction should be checked against manually labeled text spans. Security and privacy review should include access-control checks, file handling, retention, backup, and account deletion.

## 9. Discussion

The prototype's main contribution is connecting job ranking with reasons and follow-up actions in one interface. Skill overlap is explicit and relatively easy to explain. Location and experience factors make the score more useful than a text-only comparison for simple demonstrations. The candidate can also inspect missing listed skills rather than receiving a score alone. This design is aligned with research that uses profile and vacancy attributes for personalized job recommendation [1], [2].

However, demonstration value should not be confused with validated recommendation quality. A ten-listing seed dataset is not representative of a labor market. The pairwise TF-IDF-style signal is not sufficient to capture equivalent wording or skill relationships. Exact skill matching may penalize synonyms and may treat a keyword mention as evidence of skill. Résumé section extraction can fail when headings differ or a PDF contains image-only text. Feedback counts are not a substitute for precision, ranking, calibration, or fairness evaluation.

The project therefore exposes explanations, lets users edit their profile, requires consent for résumé processing, and makes deletion available. These controls support user agency and transparency. Additional review is needed before deployment with real candidates or current listings. This includes improving authentication and deployment settings, defining data retention, checking accessibility, auditing security, and evaluating whether recommendation outcomes systematically disadvantage any group.

## 10. Limitations and Future Work

The current version has a small demonstration dataset, heuristic extraction, rule-based career guidance, and no formal evaluation. It has no live data collection or automatic job refresh. Its saved search alerts are checked when the user opens the page; they do not send messages. The mini challenge checks answer structure and examples, not factual or technical correctness. The scam checker flags configured warning phrases and cannot confirm legitimacy. Market summaries describe only the local dataset.

Future work should prioritize a licensed and periodically refreshed job dataset, a corpus-based TF-IDF baseline, a manually judged evaluation set, and stronger résumé parsing with OCR only when appropriate consent and accuracy safeguards are available. Later work could compare semantic embeddings, add calibrated explanations, and evaluate fairness and user comprehension. Email, voice, generative AI, and country-specific work authorization features should be added only with appropriate service integrations, current authoritative data, and clear limitations.

## 11. Conclusion

This paper described a Flask and SQLite job recommendation and career intelligence prototype. The system combines profile data, skill overlap, lexical similarity, role preference, location, experience, and employment type to rank local sample jobs. It explains matched and missing listed skills and connects a gap to learning, evidence, interview, and application tools. Its scope is appropriate for an undergraduate software project, provided that the work is presented as a prototype and its sample data and heuristic methods are stated clearly.

The next research step is not to claim a higher score, but to evaluate the ranker against labeled relevance judgments and a reproducible baseline. Until that evaluation is completed, no accuracy or employment-success claim is supported. The system should remain a decision-support tool under user control.

## References

[1] A. Fitria, S. Zaman, and M. A. Yaqin, “Sistem Rekomendasi Lowongan Pekerjaan Menggunakan Content-Based Filtering,” *Jurnal Edukasi dan Penelitian Informatika (JEPIN)*, vol. 10, no. 3, 2024. https://doi.org/10.26418/jp.v10i3.83801.

[2] N. Kumar, M. Gupta, D. Sharma, and I. Ofori, “Technical Job Recommendation System Using APIs and Web Crawling,” *Computational Intelligence and Neuroscience*, vol. 2022, Article 7797548, 2022. https://doi.org/10.1155/2022/7797548.

[3] A. Barducci, S. Iannaccone, V. La Gatta, V. Moscato, G. Sperlì, and S. Zavota, “An end-to-end framework for information extraction from Italian resumes,” *Expert Systems with Applications*, vol. 210, Article 118487, 2022. https://doi.org/10.1016/j.eswa.2022.118487.

[4] F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” *Journal of Machine Learning Research*, vol. 12, pp. 2825–2830, 2011. https://www.jmlr.org/papers/v12/pedregosa11a.html.

[5] National Institute of Standards and Technology, *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1, 2023. https://doi.org/10.6028/NIST.AI.100-1.

## Appendix A. Example Functional Test Cases

| ID | Scenario | Expected result |
|---|---|---|
| F01 | Register with a valid unused email | Account and empty profile are created |
| F02 | Submit an incorrect password | Login is rejected without disclosing which field was wrong |
| F03 | Save a profile with duplicate skills | Profile stores deduplicated skill terms |
| F04 | Upload a text-based PDF without consent | Processing is blocked |
| F05 | Compare a profile with a job | Score, matching skills, and missing terms are shown |
| F06 | Save or unsave a job | Only the signed-in user's saved state changes |
| F07 | Import a CSV without a title or company | Invalid rows are skipped |
| F08 | Open an administrator route as a standard user | Access is denied |
| F09 | Delete an account | Account-owned profile and related database records are removed |

These are proposed test cases. They are not reported as executed results.
