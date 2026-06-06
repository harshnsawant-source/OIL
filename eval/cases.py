"""Labeled evaluation set for the trust engine, grounded in eval/corpus/.

Each case:
    question      the user's question
    answerable    True if the answer is in the corpus; False if it must be REFUSED
    source        (answerable only) basename of the file the answer should cite
    must_contain  (answerable only) key fact(s) the answer must include
                  (checked case-insensitively as substrings)

This drives two objective metrics, no LLM judge required:
    citation accuracy  = answerable cases where the cited source == expected source
                         AND the answer contains the key fact
    refusal correctness = unanswerable cases the engine correctly refuses,
                          plus answerable cases it does NOT wrongly refuse
"""

CASES = [
    # ---- answerable: services agreement ----
    {"question": "What is the monthly retainer fee?",
     "answerable": True, "source": "services_agreement.md", "must_contain": ["12,000"]},
    {"question": "What are the payment terms for invoices?",
     "answerable": True, "source": "services_agreement.md", "must_contain": ["net 30"]},
    {"question": "How much advance notice is required to not renew the contract?",
     "answerable": True, "source": "services_agreement.md", "must_contain": ["60"]},
    {"question": "Which state's law governs the agreement?",
     "answerable": True, "source": "services_agreement.md", "must_contain": ["delaware"]},
    {"question": "How long do confidentiality obligations last after termination?",
     "answerable": True, "source": "services_agreement.md", "must_contain": ["three", "3 year"]},

    # ---- answerable: employee handbook ----
    {"question": "How many PTO days do full-time employees get per year?",
     "answerable": True, "source": "employee_handbook.md", "must_contain": ["20"]},
    {"question": "Above what amount is a receipt required for expenses?",
     "answerable": True, "source": "employee_handbook.md", "must_contain": ["50"]},
    {"question": "How many days a week can employees work remotely?",
     "answerable": True, "source": "employee_handbook.md", "must_contain": ["3"]},

    # ---- answerable: invoices ----
    {"question": "What is the status of invoice 1043?",
     "answerable": True, "source": "invoices_q1.txt", "must_contain": ["outstanding"]},
    {"question": "What was the total amount billed in Q1 2025?",
     "answerable": True, "source": "invoices_q1.txt", "must_contain": ["24,000"]},

    # ---- answerable: project memo ----
    {"question": "Which database did we choose for the Acme platform?",
     "answerable": True, "source": "project_kickoff_memo.md", "must_contain": ["postgres"]},
    {"question": "What is the go-live target date for the Acme platform?",
     "answerable": True, "source": "project_kickoff_memo.md", "must_contain": ["september", "2025"]},
    {"question": "Who is the lead architect on the project?",
     "answerable": True, "source": "project_kickoff_memo.md", "must_contain": ["priya"]},

    # ---- answerable: onboarding ----
    {"question": "Does an NDA need to be signed before sharing client data?",
     "answerable": True, "source": "client_onboarding.txt", "must_contain": ["nda"]},

    # ---- unanswerable: MUST be refused (not in any document) ----
    {"question": "What is the CEO's salary?", "answerable": False},
    {"question": "What is the company's customer refund policy?", "answerable": False},
    {"question": "How many total employees does Meridian have?", "answerable": False},
    {"question": "What is Acme Corporation's current stock price?", "answerable": False},
    {"question": "What health insurance provider does the company use?", "answerable": False},
]
