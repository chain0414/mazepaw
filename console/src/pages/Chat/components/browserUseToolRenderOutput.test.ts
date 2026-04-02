import test from "node:test";
import assert from "node:assert/strict";

import { parseBrowserUseOutput } from "./browserUseToolRenderOutput.ts";

test("parses browser_use output from a JSON string", () => {
  const parsed = parseBrowserUseOutput(
    JSON.stringify({
      ok: true,
      path: "/tmp/example.png",
      image_data_url: "data:image/png;base64,abc",
    }),
  );

  assert.deepEqual(parsed, {
    ok: true,
    path: "/tmp/example.png",
    image_data_url: "data:image/png;base64,abc",
  });
});

test("parses browser_use output from a double-encoded JSON string", () => {
  const payload = JSON.stringify({
    ok: true,
    path: "/tmp/example.png",
    image_data_url: "data:image/png;base64,abc",
  });
  const parsed = parseBrowserUseOutput(JSON.stringify(payload));

  assert.deepEqual(parsed, {
    ok: true,
    path: "/tmp/example.png",
    image_data_url: "data:image/png;base64,abc",
  });
});

test("returns null for non-object payloads", () => {
  assert.equal(parseBrowserUseOutput('"just text"'), null);
  assert.equal(parseBrowserUseOutput(null), null);
});
