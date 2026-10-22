/**
 * Load test for the chat API (k6, https://k6.io). Run against the stack started with the fake model:
 *
 *   docker compose -f docker-compose.yml -f docker-compose.test.yml up -d
 *   docker run --rm -i --network sockrat_default -e BASE_URL=http://frontend:8080 \
 *     -v "$PWD/loadtest:/scripts" grafana/k6:0.54.0 run /scripts/chat.js
 *
 * Two kinds of users send messages concurrently: users without documents (prompt + model only) and
 * users with an indexed document (adds hybrid retrieval and re-ranking before the first token).
 */
import { check, sleep } from "k6";
import http from "k6/http";
import { Trend } from "k6/metrics";

const BASE = `${__ENV.BASE_URL || "http://localhost:8090"}/api`;
const USERS = Number(__ENV.USERS || 20);

const ttfbPlain = new Trend("ttfb_without_documents", true);
const ttfbRag = new Trend("ttfb_with_documents", true);
const answerTime = new Trend("full_answer_time", true);

const NOTES = `# Course handbook

## Grading
The final exam is worth 40 percent. Weekly labs are worth 30 percent.

## Office hours
Office hours are on Thursdays from 3 to 5 pm in room 4B-217.

## Final project
Project KESTREL: teams of three build a weather dashboard in Go, due December 12.
`;

const QUESTIONS = [
  "How much is the final exam worth?",
  "Where are office hours?",
  "What is Project KESTREL?",
  "Explain recursion with an example",
  "What is a list comprehension?",
];

export const options = {
  scenarios: {
    chat: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "20s", target: USERS },
        { duration: "60s", target: USERS },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    ttfb_without_documents: ["p(95)<500"],
    ttfb_with_documents: ["p(95)<2000"],
    checks: ["rate>0.99"],
  },
};

const json = { headers: { "Content-Type": "application/json" } };

function login(name) {
  http.post(`${BASE}/auth/register`, JSON.stringify({ username: name, email: `${name}@load.test`, password: "load-test-1" }), json);
  const res = http.post(`${BASE}/auth/login`, JSON.stringify({ username: name, password: "load-test-1" }), json);
  return res.json("access_token");
}

export function setup() {
  const run = Date.now();
  const users = [];
  for (let i = 0; i < USERS; i++) {
    const token = login(`load${run}u${i}`);
    const withDocs = i % 2 === 0;
    if (withDocs) {
      const upload = http.post(`${BASE}/documents`, { file: http.file(NOTES, "handbook.md", "text/markdown") }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const id = upload.json("id");
      for (let tries = 0; tries < 60; tries++) {
        const doc = http.get(`${BASE}/documents/${id}`, { headers: { Authorization: `Bearer ${token}` } });
        if (doc.json("status") === "ready") break;
        sleep(0.5);
      }
    }
    users.push({ token, withDocs });
  }
  return { users };
}

export default function (data) {
  const user = data.users[(__VU - 1) % data.users.length];
  const auth = { headers: { "Content-Type": "application/json", Authorization: `Bearer ${user.token}` } };

  const session = http.post(`${BASE}/chat/sessions`, "{}", auth);
  check(session, { "session created": (r) => r.status === 201 });

  const question = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const res = http.post(`${BASE}/chat/sessions/${session.json("id")}/messages`, JSON.stringify({ message: question }), {
    ...auth,
    tags: { name: "send_message" },
    timeout: "60s",
  });
  check(res, {
    "answer streamed": (r) => r.status === 200 && r.body.includes('"type": "done"'),
  });
  (user.withDocs ? ttfbRag : ttfbPlain).add(res.timings.waiting);
  answerTime.add(res.timings.duration);

  http.get(`${BASE}/chat/sessions`, auth);
  sleep(1);
}
