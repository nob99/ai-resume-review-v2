// Optional: configure or set up a testing framework before each test.
// If you delete this file, remove `setupFilesAfterEnv` from `jest.config.js`

// Used for __tests__/testing-library.js
// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Add missing globals for MSW
import { TextEncoder, TextDecoder } from 'util'
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// Add fetch polyfill
import 'whatwg-fetch'

// Mock TransformStream for tests
global.TransformStream = class TransformStream {
  constructor() {
    this.readable = {}
    this.writable = {}
  }
}