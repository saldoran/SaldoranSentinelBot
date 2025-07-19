#!/bin/bash

INSTANCE_ID="i-06b38b6d9703a46ed"
REGION="eu-north-1"

case "$1" in
  start)
    echo "Starting instance $INSTANCE_ID..."
    aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION
    echo "Start command sent."
    ;;
  stop)
    echo "Stopping instance $INSTANCE_ID..."
    aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION
    echo "Stop command sent."
    ;;
  restart)
    echo "Rebooting instance $INSTANCE_ID..."
    aws ec2 reboot-instances --instance-ids $INSTANCE_ID --region $REGION
    echo "Reboot command sent."
    ;;
  status)
    echo "Checking instance status..."
    aws ec2 describe-instance-status \
      --instance-ids $INSTANCE_ID \
      --include-all-instances \
      --region $REGION \
      --query 'InstanceStatuses[0].InstanceState.Name' \
      --output text
    ;;
  *)
    echo "Unknown command. Use: start | stop | restart | status"
    ;;
esac