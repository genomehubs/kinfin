// setupTests.js
import "@testing-library/jest-dom";
// Polyfill TextEncoder/TextDecoder for jest/jsdom environment
if (typeof global.TextEncoder === "undefined") {
  const { TextEncoder, TextDecoder } = require("util");
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}
