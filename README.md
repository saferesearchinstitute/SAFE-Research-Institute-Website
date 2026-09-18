# SAFE Research Institute Website

Public website of the Science and Freedom for Everyone Foundation (saferi.org), a California nonprofit public benefit corporation. 501(c)(3) application pending.

Static HTML/CSS/JS site. Volunteer intake backed by Firebase (Firestore + a Cloud Function email notifier). Hosted on Vercel; `firebase.json` also configures the Firestore rules and functions deploy.

- Educational articles, research summaries, and recorded presentations
- Model policy document library (educational reference, CC0)
- Volunteer application and admin queue

Content licenses: model policy documents CC0 1.0; research and educational materials CC BY 4.0; software GPL-3.0 (see LICENSE). The Foundation's names and logos are reserved.

Deploy: `vercel --prod` from the repo root. Firestore rules/functions: `firebase deploy --only firestore,functions`.
