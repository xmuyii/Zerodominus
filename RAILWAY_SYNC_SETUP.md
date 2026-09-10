# Railway Auto-Sync Setup (Supabase → Google Sheets → WhatsAuto)

## Overview
This guide sets up automatic syncing from Supabase to Google Sheets on Railway, which WhatsAuto will monitor and use to send WhatsApp messages.

**Flow:** Supabase → Railway (cron job) → Google Sheets → WhatsAuto → WhatsApp

## Step 1: Verify Google Sheets Config in `.env`

Your `.env` already has:
```
GOOGLE_SHEET_ID=1pQtLTKFlSJIDWaxe8P3UtjPI6AB-2AEJDEphSjHlvK0
GOOGLE_SHEET_NAME=Leaderboard
GOOGLE_CREDENTIALS_PATH=./google-credentials.json
SUPABASE_URL=https://basniiolppmtpzishhtn.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

✅ All required config is present!

## Step 2: Upload `google-credentials.json` to Railway

1. Download your Google Service Account JSON key (if you don't have it):
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to **Service Accounts**
   - Select your service account
   - Go to **Keys** tab
   - Click **Add Key** → **Create new key** → **JSON**
   - Save the file

2. Share your Google Sheet with the service account email:
   - Open the JSON file and find the `client_email` field
   - Go to your Google Sheet
   - Click **Share**
   - Paste the service account email and give it **Editor** access

3. Upload to Railway:
   - In Railway dashboard, go to your project
   - Add the `google-credentials.json` file to the repository or upload as a secret in Railway

## Step 3: Add Railway Cron Job for Hourly Sync

**Option A: Using Railway Cron Jobs (Recommended)**

1. In your Railway project, create a new **Cron Job**:
   ```
   Name: Supabase-to-Sheets Sync
   Command: python sync_to_sheets.py
   Schedule: 0 * * * * (every hour at minute 0)
   ```

2. Ensure the cron job has access to:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SHEET_NAME`
   - `GOOGLE_CREDENTIALS_PATH` (with the JSON file)

**Option B: Using a Webhook Trigger**

1. Create a simple Flask endpoint in `main.py` or a separate service:
   ```python
   from flask import Flask, jsonify
   
   app = Flask(__name__)
   
   @app.route('/sync-sheets', methods=['POST'])
   def sync_sheets():
       from sync_to_sheets import main
       success = main()
       return jsonify({"status": "success" if success else "failed"})
   
   if __name__ == '__main__':
       app.run(port=5000)
   ```

2. Configure Railway webhook to call this endpoint:
   - Endpoint: `https://your-railway-domain.com/sync-sheets`
   - Method: `POST`
   - Schedule: Hourly

## Step 4: Configure WhatsAuto to Monitor Google Sheet

1. Open your Google Sheet
2. Set up WhatsAuto automation:
   - **Trigger:** When column "Trigger" = "leaderboard", "weekly", "scores", or "rank"
   - **Action:** Send the corresponding "Response" text to your WhatsApp group
   - **Update frequency:** Check every 5-10 minutes

## Step 5: Test the Sync

**Local test:**
```bash
python sync_to_sheets.py
```

**Railway test:**
- Manually run the cron job in Railway dashboard
- Check Google Sheet for updated leaderboard
- Verify WhatsAuto sends the message to WhatsApp

## Troubleshooting

### Google Sheets API Error
- Verify service account has **Editor** access to the sheet
- Check `GOOGLE_CREDENTIALS_PATH` points to valid JSON file

### Supabase Connection Failed
- Verify `SUPABASE_URL` and `SUPABASE_KEY` in Railway environment
- Check Supabase project is active and accessible

### No Players in Leaderboard
- Ensure players have `weekly_points > 0`
- Check `week_start` matches current week

### WhatsAuto Not Triggering
- Verify trigger keywords match exactly (case-sensitive)
- Ensure WhatsAuto formula is set to monitor the "Trigger" column
- Check WhatsAuto update frequency is < 10 minutes

## Monitoring

Check sync logs in Railway:
```
railway logs --follow
```

Look for:
- `✅ Google Sheet updated successfully`
- `Found X players` in the output

## Next Steps

1. ✅ Verify `.env` has all config
2. ✅ Upload `google-credentials.json` to Railway
3. ✅ Create cron job on Railway to run `sync_to_sheets.py` hourly
4. ✅ Test the sync manually
5. ✅ Configure WhatsAuto to monitor the sheet
6. ✅ You're done! Leaderboard will sync automatically when you're away
