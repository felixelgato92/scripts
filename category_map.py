from typing import List, Set

CATEGORY_MAP: List[tuple] = [
    # Income / Payroll
    ("advancedmd inc payroll",    "Paycheck"),
    ("payroll",                   "Paycheck"),
    ("direct dep",                "Paycheck"),

    # Donations
    ("donation",                  "Donations"),
    ("charity",                   "Donations"),
    ("ch jesuschrist",            "Donations"),

    # Short-term rental
    ("airbnb",                    "Short-Term Rental"),
    ("vrbo",                      "Short-Term Rental"),
    ("turno",                     "Short-Term Rental"),
    ("booking.com",               "Short-Term Rental"),
    ("check",                     "Checks"),

    # Housing
    ("mortgage",                  "Mortgage"),
    ("escrow",                    "Mortgage"),
    ("pennymac",                  "Mortgage"),
    ("planet home",               "Mortgage"),
    ("fidelity",                  "Loan"),
    ("dept education student ln", "Loan"),
    ("hoa",                       "Housing"),

    # Utilities & bills
    ("electric",                  "Bills & Utilities"),
    ("water",                     "Bills & Utilities"),
    ("gas bill",                  "Bills & Utilities"),
    ("internet",                  "Bills & Utilities"),
    ("spectrum",                  "Bills & Utilities"),
    ("comcast",                   "Bills & Utilities"),
    ("at&t",                      "Bills & Utilities"),
    ("t-mobile",                  "Bills & Utilities"),
    ("verizon",                   "Bills & Utilities"),
    ("xfinity",                   "Bills & Utilities"),
    ("i3broadband",               "Bills & Utilities"),
    ("amerenillinois",            "Bills & Utilities"),
    ("amerenil",                  "Bills & Utilities"),
    ("utility",                   "Bills & Utilities"),
    ("psn*city",                  "Bills & Utilities"),
    ("illinois-america payment ppd", "Bills & Utilities"),

    # Subscriptions
    ("peacock",                   "Subscriptions"),
    ("netflix",                   "Subscriptions"),
    ("hulu",                      "Subscriptions"),
    ("spotify",                   "Subscriptions"),
    ("disney+",                   "Subscriptions"),
    ("apple.com/bill",            "Subscriptions"),

    # Insurance
    ("insurance",                 "Insurance"),
    ("geico",                     "Insurance"),
    ("state farm",                "Insurance"),
    ("allstate",                  "Insurance"),
    ("progressive",               "Insurance"),

    # Groceries
    ("walmart",                   "Groceries"),
    ("wm supercenter",            "Groceries"),
    ("kroger",                    "Groceries"),
    ("aldi",                      "Groceries"),
    ("publix",                    "Groceries"),
    ("costco",                    "Groceries"),
    ("sam's club",                "Groceries"),
    ("target",                    "Groceries"),
    ("whole foods",               "Groceries"),
    ("trader joe",                "Groceries"),

    # Food & Drink
    ("mcdonald",                  "Food & Drink"),
    ("chick-fil-a",               "Food & Drink"),
    ("taco bell",                 "Food & Drink"),
    ("starbucks",                 "Food & Drink"),
    ("dunkin",                    "Food & Drink"),
    ("pizza",                     "Food & Drink"),
    ("wendy",                     "Food & Drink"),
    ("chipotle",                  "Food & Drink"),
    ("subway",                    "Food & Drink"),
    ("doordash",                  "Food & Drink"),
    ("uber eats",                 "Food & Drink"),
    ("grubhub",                   "Food & Drink"),
    ("restaurant",                "Food & Drink"),

    # Gas / Auto
    ("shell oil",                 "Gas"),
    ("chevron",                   "Gas"),
    ("exxon",                     "Gas"),
    ("bp ",                       "Gas"),
    ("speedway",                  "Gas"),
    ("circle k",                  "Gas"),
    ("fuel",                      "Gas"),
    ("gas station",               "Gas"),

    # Shopping
    ("amazon",                    "Shopping"),
    ("amzn",                      "Shopping"),
    ("best buy",                  "Shopping"),
    ("home depot",                "Shopping"),
    ("lowes",                     "Shopping"),
    ("ikea",                      "Shopping"),

    # Transfers
    ("transfer",                  "Transfer"),
    ("zelle",                     "Transfer"),
    ("venmo",                     "Transfer"),
    ("paypal",                    "Transfer"),
    ("cashapp",                   "Transfer"),
    ("cash app",                  "Transfer"),

    # Fees
    ("service charge",            "Fees & Adjustments"),
    ("atm fee",                   "Fees & Adjustments"),
    ("overdraft",                 "Fees & Adjustments"),
    ("monthly fee",               "Fees & Adjustments"),
    ("interest charge",           "Fees & Adjustments"),

    # Health
    ("pharmacy",                  "Health"),
    ("cvs",                       "Health"),
    ("walgreens",                 "Health"),
    ("doctor",                    "Health"),
    ("medical",                   "Health"),
    ("dental",                    "Health"),
    ("hospital",                  "Health"),

    # Travel
    ("airline",                   "Travel"),
    ("hotel",                     "Travel"),
    ("uber trip",                 "Travel"),
    ("lyft",                      "Travel"),
]

CATEGORIES: Set[str] = {category for _, category in CATEGORY_MAP} | {"Uncategorized"}