interface FollowUpTopic {
  topic: string | null;
  question: string;
}

interface SchemeFollowUps {
  topics: FollowUpTopic[];
}

const SCHEMES: Record<string, SchemeFollowUps> = {
  "HDFC FlexiCap Fund": {
    topics: [
      // FAQ-3
      { topic: "investment_objective", question: "What is the investment objective of HDFC Flexi Cap Fund?" },
      // FAQ-4
      { topic: "minimum_investment", question: "What is the minimum SIP amount for HDFC Flexi Cap Fund?" },
      // FAQ-5
      { topic: "minimum_investment", question: "What is the minimum lump-sum purchase amount for HDFC Flexi Cap Fund?" },
      // FAQ-6
      { topic: "expense_ratio", question: "What is the Total Expense Ratio (TER) of HDFC Flexi Cap Fund under the Direct Plan?" },
      // FAQ-8
      { topic: "exit_load", question: "What is the exit load of HDFC Flexi Cap Fund and what holding duration applies?" },
      // FAQ-9
      { topic: "riskometer", question: "What is the current SEBI Risk-o-meter rating of HDFC Flexi Cap Fund?" },
      // FAQ-10
      { topic: "benchmark", question: "What is the official benchmark of HDFC Flexi Cap Fund?" },
      // FAQ-11
      { topic: "asset_allocation", question: "What is the asset allocation of HDFC Flexi Cap Fund?" },
      // FAQ-12
      { topic: "lock_in", question: "Does HDFC Flexi Cap Fund have a lock-in period?" },
      // FAQ-17
      { topic: "plans_options", question: "What plans and options are available for HDFC Flexi Cap Fund?" },
      // FAQ-13
      { topic: null, question: "How can I invest in HDFC Flexi Cap Fund?" },
      // FAQ-16
      { topic: "redemption", question: "How can I redeem HDFC Flexi Cap Fund units?" },
    ],
  },
  "HDFC Small Cap Fund": {
    topics: [
      // FAQ-20
      { topic: "investment_objective", question: "What is the investment objective of HDFC Small Cap Fund?" },
      // FAQ-21
      { topic: "minimum_investment", question: "What is the minimum SIP amount for HDFC Small Cap Fund?" },
      // FAQ-22
      { topic: "minimum_investment", question: "What is the minimum lump-sum purchase amount for HDFC Small Cap Fund?" },
      // FAQ-23
      { topic: "expense_ratio", question: "What is the Total Expense Ratio (TER) of HDFC Small Cap Fund under the Direct Plan?" },
      // FAQ-25
      { topic: "exit_load", question: "What is the exit load of HDFC Small Cap Fund and what holding duration applies?" },
      // FAQ-26
      { topic: "riskometer", question: "What is the current SEBI Risk-o-meter rating of HDFC Small Cap Fund?" },
      // FAQ-27
      { topic: "benchmark", question: "What is the official benchmark of HDFC Small Cap Fund?" },
      // FAQ-29
      { topic: "asset_allocation", question: "What is the asset allocation of HDFC Small Cap Fund?" },
      // FAQ-30
      { topic: "lock_in", question: "Does HDFC Small Cap Fund have a lock-in period?" },
      // FAQ-35
      { topic: "plans_options", question: "What plans and options are available for HDFC Small Cap Fund?" },
      // FAQ-31
      { topic: null, question: "How can I invest in HDFC Small Cap Fund?" },
      // FAQ-34
      { topic: "redemption", question: "How can I redeem HDFC Small Cap Fund units?" },
    ],
  },
  "HDFC Large and Mid Cap Fund": {
    topics: [
      // FAQ-38
      { topic: "investment_objective", question: "What is the investment objective of HDFC Large and Mid Cap Fund?" },
      // FAQ-39
      { topic: "minimum_investment", question: "What is the minimum SIP amount for HDFC Large and Mid Cap Fund?" },
      // FAQ-40
      { topic: "minimum_investment", question: "What is the minimum lump-sum purchase amount for HDFC Large and Mid Cap Fund?" },
      // FAQ-41
      { topic: "expense_ratio", question: "What is the Total Expense Ratio (TER) of HDFC Large and Mid Cap Fund under the Direct Plan?" },
      // FAQ-43
      { topic: "exit_load", question: "What is the exit load of HDFC Large and Mid Cap Fund and what holding duration applies?" },
      // FAQ-44
      { topic: "riskometer", question: "What is the current SEBI Risk-o-meter rating of HDFC Large and Mid Cap Fund?" },
      // FAQ-45
      { topic: "benchmark", question: "What is the official benchmark of HDFC Large and Mid Cap Fund?" },
      // FAQ-46
      { topic: "asset_allocation", question: "What is the asset allocation of HDFC Large and Mid Cap Fund?" },
      // FAQ-47
      { topic: "lock_in", question: "Does HDFC Large and Mid Cap Fund have a lock-in period?" },
      // FAQ-52
      { topic: "plans_options", question: "What plans and options are available for HDFC Large and Mid Cap Fund?" },
      // FAQ-48
      { topic: null, question: "How can I invest in HDFC Large and Mid Cap Fund?" },
      // FAQ-51
      { topic: "redemption", question: "How can I redeem HDFC Large and Mid Cap Fund units?" },
    ],
  },
  "HDFC Index Fund - Nifty 50 Plan": {
    topics: [
      // FAQ-55
      { topic: "investment_objective", question: "What is the investment objective of HDFC Nifty 50 Index Fund?" },
      // FAQ-56
      { topic: "minimum_investment", question: "What is the minimum SIP amount for HDFC Nifty 50 Index Fund?" },
      // FAQ-57
      { topic: "minimum_investment", question: "What is the minimum lump-sum purchase amount for HDFC Nifty 50 Index Fund?" },
      // FAQ-58
      { topic: "expense_ratio", question: "What is the Total Expense Ratio (TER) of HDFC Nifty 50 Index Fund under the Direct Plan?" },
      // FAQ-60
      { topic: "exit_load", question: "What is the exit load of HDFC Nifty 50 Index Fund and what holding duration applies?" },
      // FAQ-61
      { topic: "riskometer", question: "What is the current SEBI Risk-o-meter rating of HDFC Nifty 50 Index Fund?" },
      // FAQ-62
      { topic: "benchmark", question: "What is the official benchmark of HDFC Nifty 50 Index Fund?" },
      // FAQ-63
      { topic: "asset_allocation", question: "What is the asset allocation of HDFC Nifty 50 Index Fund?" },
      // FAQ-64
      { topic: "lock_in", question: "Does HDFC Nifty 50 Index Fund have a lock-in period?" },
      // FAQ-72
      { topic: "plans_options", question: "What plans and options are available for HDFC Nifty 50 Index Fund?" },
      // FAQ-65
      { topic: "tracking_error", question: "What is the tracking error of HDFC Nifty 50 Index Fund?" },
      // FAQ-67
      { topic: "replication", question: "What is the replication strategy of HDFC Nifty 50 Index Fund?" },
      // FAQ-68
      { topic: null, question: "How can I invest in HDFC Nifty 50 Index Fund?" },
      // FAQ-71
      { topic: "redemption", question: "How can I redeem HDFC Nifty 50 Index Fund units?" },
    ],
  },
  "HDFC ELSS Tax Saver Fund": {
    topics: [
      // FAQ-75
      { topic: "investment_objective", question: "What is the investment objective of HDFC ELSS Tax Saver Fund?" },
      // FAQ-76
      { topic: "minimum_investment", question: "What is the minimum SIP amount for HDFC ELSS Tax Saver Fund?" },
      // FAQ-77
      { topic: "minimum_investment", question: "What is the minimum lump-sum purchase amount for HDFC ELSS Tax Saver Fund?" },
      // FAQ-78
      { topic: "expense_ratio", question: "What is the Total Expense Ratio (TER) of HDFC ELSS Tax Saver Fund under the Direct Plan?" },
      // FAQ-80
      { topic: "exit_load", question: "What is the exit load of HDFC ELSS Tax Saver Fund and what holding duration applies?" },
      // FAQ-81
      { topic: "riskometer", question: "What is the current SEBI Risk-o-meter rating of HDFC ELSS Tax Saver Fund?" },
      // FAQ-82
      { topic: "benchmark", question: "What is the official benchmark of HDFC ELSS Tax Saver Fund?" },
      // FAQ-83
      { topic: "asset_allocation", question: "What is the asset allocation of HDFC ELSS Tax Saver Fund?" },
      // FAQ-84
      { topic: "lock_in", question: "What is the lock-in period of HDFC ELSS Tax Saver Fund?" },
      // FAQ-86
      { topic: "fund_manager", question: "Who manages HDFC ELSS Tax Saver Fund?" },
      // FAQ-92
      { topic: "plans_options", question: "What plans and options are available for HDFC ELSS Tax Saver Fund?" },
      // FAQ-88
      { topic: null, question: "How can I invest in HDFC ELSS Tax Saver Fund?" },
      // FAQ-155
      { topic: "redemption", question: "How can I redeem HDFC ELSS Tax Saver Fund units?" },
    ],
  },
};

export const GENERAL_FALLBACKS = [
  "What is the difference between SIP and lump-sum investment?",
  "What are the six risk levels shown on the SEBI Risk-o-meter?",
  "What is the difference between the Growth option and the IDCW option?",
];

export function getFollowUps(scheme: string | null, excludeTopic: string | null): string[] {
  const entry = scheme ? SCHEMES[scheme] : undefined;
  if (!entry) return GENERAL_FALLBACKS;
  return entry.topics
    .filter((t) => !excludeTopic || t.topic !== excludeTopic)
    .slice(0, 3)
    .map((t) => t.question);
}
