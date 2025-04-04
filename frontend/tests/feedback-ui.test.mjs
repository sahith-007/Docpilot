import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const appSource = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const apiSource = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");

test("feedback buttons render selected state and per-action saving state", () => {
  assert.match(appSource, /activeFeedback === "accepted"/);
  assert.match(appSource, /activeFeedback === "review"/);
  assert.match(appSource, /activeFeedback === "rejected"/);
  assert.match(appSource, /savingFeedback === "accepted"/);
  assert.match(appSource, /savingFeedback === "review"/);
  assert.match(appSource, /savingFeedback === "rejected"/);
});

test("feedback click persists the latest status from the API response", () => {
  assert.match(appSource, /api\.feedback\(session\.token, answerId, status\)/);
  assert.match(appSource, /feedback_status: response\.status/);
  assert.match(appSource, /feedback_message: response\.message/);
  assert.match(appSource, /feedback_updated_at: response\.updated_at/);
  assert.match(apiSource, /status,/);
  assert.doesNotMatch(appSource, /"Review saved"\s*\)/);
});

test("assistant cards hide raw model names and format limitations", () => {
  assert.match(appSource, /function getAssistantLabel/);
  assert.match(appSource, /DocPilot AI/);
  assert.match(appSource, /DocPilot Demo/);
  assert.doesNotMatch(appSource, /<span>\{message\.model/);
  assert.match(appSource, /function formatLimitations/);
  assert.match(appSource, /limitationItems\.map/);
  assert.match(appSource, /<li key=\{limit\}>/);
  assert.doesNotMatch(appSource, /message\.limits\.join\(" "\)/);
});
