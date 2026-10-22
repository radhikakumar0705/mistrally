#!/usr/bin/env bash
# Sign-up + login latency while answers are streaming: 8 concurrent sign-ups during 6 active streams.
# Usage: loadtest/auth_under_load.sh [base_url]
set -u
B="${1:-http://127.0.0.1:8090}/api"

U=streamer$RANDOM
curl -s -o /dev/null -X POST "$B/auth/register" -H "Content-Type: application/json" \
  -d "{\"username\":\"$U\",\"email\":\"$U@x.test\",\"password\":\"probepass1\"}"
TOK=$(curl -s -X POST "$B/auth/login" -H "Content-Type: application/json" \
  -d "{\"username\":\"$U\",\"password\":\"probepass1\"}" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

for i in 1 2 3 4 5 6; do
  (SID=$(curl -s -X POST "$B/chat/sessions" -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -d '{}' \
     | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
   curl -s -o /dev/null -X POST "$B/chat/sessions/$SID/messages" -H "Authorization: Bearer $TOK" \
     -H "Content-Type: application/json" -d '{"message":"keep streaming"}') &
done
sleep 0.5

for i in 1 2 3 4 5 6 7 8; do
  (N=auth$RANDOM$i
   curl -s -o /dev/null -w "%{time_total}\n" -X POST "$B/auth/register" -H "Content-Type: application/json" \
     -d "{\"username\":\"$N\",\"email\":\"$N@x.test\",\"password\":\"probepass1\"}"
   curl -s -o /dev/null -w "%{time_total}\n" -X POST "$B/auth/login" -H "Content-Type: application/json" \
     -d "{\"username\":\"$N\",\"password\":\"probepass1\"}") &
done | sort -n | python -c "
import sys
t = [float(x) for x in sys.stdin if x.strip()]
print(f'auth requests: {len(t)}  median {t[len(t)//2]:.2f}s  max {t[-1]:.2f}s')"
wait
