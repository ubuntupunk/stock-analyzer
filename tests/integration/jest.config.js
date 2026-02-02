module.exports = {
  preset: 'jest-playwright-preset',
  testEnvironment: './custom-environment.js',
  testMatch: ['**/*.test.js'],
  testTimeout: 60000,
  setupFilesAfterEnv: ['./jest.setup.js'],
  verbose: true,
  collectCoverageFrom: [
    '../../infrastructure/frontend/modules/**/*.js',
    '!**/*.test.js'
  ]
};
