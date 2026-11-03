# Login recovery

The release never contains production database credentials or a default password. Configure `backend/web.config` first and verify that `DATABASE_URL` points to the intended database.

From the release backend directory, run:

```powershell
.\runtime\SupportHubBackend.exe migrate
.\runtime\SupportHubBackend.exe seed
.\runtime\SupportHubBackend.exe recover-admin --login admin --email admin@example.com
```

Enter the new password twice when prompted. It must contain at least 12 characters. If the account already exists, `--email` is optional; the command resets its password, activates it, clears its lockout, and requires a password change after login. If it does not exist, the command creates an Administrator account after seed data is available.

Then restart the IIS application pool and sign in with the supplied username or email. Do not place the password in scripts, command history, `web.config`, or this project.
