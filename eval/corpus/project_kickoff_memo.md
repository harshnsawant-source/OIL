# Project Kickoff Memo — Acme Data Platform

**Date:** March 10, 2025
**Author:** Priya Nair, Lead Architect

## Decision
After evaluating options, we will use **PostgreSQL** as the primary datastore
for the Acme data platform. We considered MongoDB but chose PostgreSQL because
the workload requires strong relational integrity and complex multi-table joins,
which fit a relational model better.

## Target
Go-live target date: **September 1, 2025.**

## Team
- Priya Nair — Lead Architect
- Daniel Osei — Backend Engineer
- Lena Park — Data Engineer

## Top Risk
The largest risk is migrating ~8 years of records from Acme's legacy MySQL
system. Mitigation: a phased migration with a dual-write period and automated
row-count reconciliation before cutover.
