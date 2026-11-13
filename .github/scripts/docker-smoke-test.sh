#!/bin/bash
set -e

output=$(timeout --signal=INT 3s docker compose -f .github/smoke_test/docker-compose.ci.yml \
run --rm -T -e USE_MONGO=0 test < new_test/docker_input.txt 2>&1 || true)
# [STATUS] NEW MODIFY
#__ The new startup fixture explicitly creates an offline household before profiles.
#timeout will send interupt signal afer 3 second, || true ensures rest of this script runs if docker test fails
echo "$output" #prints outpout of test to terminal 

if echo "$output" | grep -Fq 'Use a household ID such as HS-7K9M-2X4P-8R6T.'; then
  echo "Smoke test passed: expectd prompt returned" #successful if execution returns exit 0 by defualt
else
echo "Smoke test failed: expected prompt not reached."
exit 1
fi
