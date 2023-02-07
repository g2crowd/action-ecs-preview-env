#!/bin/sh -l
set -e

RESULT="false"

if [ "$1" = "deploy" ]; then
  python /src/main.py "$1" --org "$2" --repo "$3" --branch "$4" --pr "$5" --author "$6" --image "$7" --sha "$8" --assume "$9" --tfstate "${10}"
elif [ "$1" = "undeploy" ]; then
  python /src/main.py "$1" --org "$2" --repo "$3" --pr "$5" --sha "$8" --assume "$9" --tfstate "${10}"
else
   echo "[error] Unknown command"
   exit 1
fi

BUILD_RESULT=$?
if [ $BUILD_RESULT -eq 0 ]; then
  RESULT="true"
fi

export $(cat .env.prenv | xargs)
echo $RESULT
echo $TASK_ARN
echo ::set-output name=success::$RESULT
echo ::set-output name=task_arn::$TASK_ARN
