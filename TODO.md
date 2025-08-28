# Fix React Object Rendering Error

## Steps to Complete:

1. [ ] Update App.jsx state to store the full response object instead of just answer string
2. [ ] Update handleAsk function to set the full response
3. [ ] Update rendering logic to display answer, score, and sources properly
4. [ ] Test the application to ensure error is resolved

## Current Issue:

- Backend returns: {answer: string, score: number, sources: array}
- Frontend was trying to render the entire object instead of just the answer string
- React cannot render objects directly - causes "Objects are not valid as a React child" error

## Solution:

- Store the full response object in state
- Render the answer property as string
- Optionally display score and sources for better UX
