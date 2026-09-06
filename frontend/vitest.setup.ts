import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

afterEach(() => {
  cleanup();
});

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (!global.ResizeObserver) {
  global.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

Object.defineProperties(HTMLElement.prototype, {
  offsetWidth: { configurable: true, value: 600 },
  offsetHeight: { configurable: true, value: 220 },
});
