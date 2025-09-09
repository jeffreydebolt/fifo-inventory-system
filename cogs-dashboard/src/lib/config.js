// Single source of truth for API base in the frontend
export const API_BASE =
  process.env.REACT_APP_API_URL ||
  process.env.REACT_APP_API_BASE_URL ||    // accept either name
  'https://api.firstlot.co';               // safe default for prod