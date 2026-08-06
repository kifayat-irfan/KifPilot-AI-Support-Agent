# Frontend Tests

This directory contains tests for the frontend application.

## Running Tests

```bash
# Run all tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm test -- --watch
```

## Test Structure

- `setup.ts` - Test setup and global mocks
- `components/` - Component tests
- `hooks/` - Custom hook tests
- `services/` - Service tests
- `store/` - Store tests
- `utils/` - Utility function tests