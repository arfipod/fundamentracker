#!/bin/bash

# 1. Start the API and the tunnel in the background
echo "Starting containers..."
docker-compose up -d api cloudflared

# 2. Wait for the tunnel to generate the URL
echo "Waiting for Cloudflare to generate the URL..."
sleep 5

# 3. Extract the trycloudflare URL from the logs
CF_URL=$(docker-compose logs cloudflared | grep -Eo 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -n 1)

if [ -z "$CF_URL" ]; then
    echo "❌ Failed to get Cloudflare URL. Check the logs with: docker-compose logs cloudflared"
    exit 1
fi

echo "✅ Tunnel successfully created at: $CF_URL"

# 4. Update the environment variable in Vercel
echo "🔄 Updating VITE_API_URL variable in Vercel..."

# Remove the previous variable (ignoring the error if it does not exist)
vercel env rm VITE_API_URL production -y > /dev/null 2>&1

# Add the new variable
echo "$CF_URL" | vercel env add VITE_API_URL production

echo "✅ Variable updated in Vercel."
echo "🚀 Remember to deploy again in Vercel (e.g. running 'vercel --prod') so the changes apply to the frontend."