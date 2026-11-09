// Jest setup: in-memory AsyncStorage so preference code runs without a device.
jest.mock('@react-native-async-storage/async-storage', () =>
  // jest.mock factories must be synchronous, so require() is the only option here.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);
