#!/bin/bash
set -e
imageName=apiservices

# Start the nginx server
nginx -g 'daemon off;' 2>&1 | tee /app/nginx.log &

# Start the Public API Server
uvicorn app.main:server --host 0.0.0.0 --port 8000

# To keep the container running
tail -f /dev/null
