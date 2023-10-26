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
  echo ::set-output name=lastStatus::"Running"
else
  echo ::set-output name=lastStatus::"Stopped"
fi

export $(cat .prenv_vars | xargs)
echo $RESULT
echo $TASK_ARN
echo $TASK_ID
echo $RESULT
echo $CLUSTER
echo $SUBNETS
echo $SECURITY_GROUPS
echo $TASK_DEFINITION
echo $STARTED_BY
echo ::set-output name=success::$RESULT
echo ::set-output name=arn::$TASK_ARN
echo ::set-output name=taskId::$TASK_ID
echo ::set-output name=cluster::$CLUSTER
echo ::set-output name=subnets::$SUBNETS
echo ::set-output name=securityGroups::$SECURITY_GROUPS
echo ::set-output name=taskDefinition::$TASK_DEFINITION
echo ::set-output name=startedBy::$STARTED_BY
