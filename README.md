# CTFd AI Submissions Plugin (AI Link)

Self-contained plugin for **CTFd** that adds a mandatory **"AI Link"** field to every flag submission.

Designed to enforce competition rules: participants must include the **URL of the AI tool used** (e.g. ChatGPT, etc.) when working on or solving a challenge. The value is stored in the database and linked to each submission, so organizers can audit "which challenge was solved using which AI".

> **Important:** This plugin is 100% self-contained. It does **not** modify any CTFd core or theme files. All injection happens from the plugin folder itself (`/plugins/ai_submissions`). Safe to install on a running event.

- [Bahasa Indonesia](README.id.md)

---

## Features

- **Backend (theme-agnostic, works on all CTFd themes):**
  - Stores `ai_link` in the `ai_links` table, linked to every submission (solve, fail, partial, rate-limited).
  - Server-side validation: submissions **without** `ai_link` are **blocked** (HTTP 400), enforcing the AI Link even if the frontend is bypassed.
  - Works in both **user** and **teams** modes (auto-detected via CTFd `user_mode`).
  - **Dynamic challenges**: points are counted including the AI Link submission.
  - **"AI Link"** column shown directly in **Admin → Submissions** (`/admin/submissions`), merged into **All / Correct / Incorrect** views, no separate menu. Data is fetched via the plugin JSON endpoint `/admin/ai-submissions/links?submission_ids=...` (admin only).
  - Full review page `/admin/ai-submissions` remains available (admin only), accessible via direct URL (no header menu).
  - Admin challenge **preview** is excluded from validation, so admin review does not require an AI Link.

- **Frontend (field rendering):**
  - **"AI Link\*"** field injected into the challenge modal via plugin JavaScript (self-contained in the plugin folder).

---

## Folder Structure

```
ai_submissions/
├── __init__.py                     # Plugin logic (registration, backend, admin bp)
├── assets/
│   ├── ai_submissions.js           # Frontend JS: inject AI Link field into the modal
│   └── ai_submissions_admin.js     # Admin JS: inject AI Link column in /admin/submissions
└── templates/
    └── ai_submissions.html         # Admin review page /admin/ai-submissions
```

---

## Requirements

- Docker + docker-compose running **CTFd** (ctfd:latest).

---

## Installation

1. **Place the plugin folder** into the CTFd plugins path. With docker-compose (e.g. project `ctfd`):

   ```
   # from the host, copy the folder into the dir mounted to the container
   cp -r ai_submissions /path/project/CTFd/CTFd/plugins/
   ```

   or copy directly into the container (if there is no volume mount):

   ```
   docker cp ai_submissions ctfd-ctfd-1:/opt/CTFd/CTFd/plugins/
   ```

   Replace `ctfd-ctfd-1` with your CTFd container name (check via `docker ps`).

2. **Restart CTFd** so the plugin is loaded:

   ```
   docker-compose restart ctfd
   # or
   docker restart <ctfd-container-name>
   ```

3. **Verify it is installed.** Open the login/challenges page in a browser.
   - Backend validation works on all themes.
   - Frontend field verified working on the `pixo` theme. See [Supported Themes](#supported-themes).

4. **Check the database table (once).** The plugin creates the `ai_links` table automatically on first load. No manual migration needed.

---

## Usage

1. Log in as a participant (user or team).
2. Open the **Challenges** page.
3. Click a challenge.
4. Fill in **AI Link** (an http/https URL of the AI used) and then the flag.
5. Submit. Without an AI Link the submission is **rejected** (frontend alert + backend rejection).

---

## Supported Themes

| Theme | Status |
|---|---|
| `pixo` | **Fully supported** |
| `core-deprecated` | **Fully supported** |

For other themes: backend validation works everywhere. To render the frontend field, adjust the single plugin JS file (still without touching any core theme).

---

## Status / Debug

- Check container logs:

  ```
  docker logs ctfd-ctfd-1 --tail 100
  ```

- Check from inside the container whether the plugin is loaded:

  ```
  docker exec ctfd-ctfd-1 python -c "from CTFd import create_app; app=create_app(); print('plugins:', [p for p in app.plugins])"
  ```

- Check the database (`ai_links` table):

  ```
  docker exec ctfd-db-1 mariadb -uctfd -pctfd ctfd -e "SELECT * FROM ai_links;"
  ```

---

## Uninstall

1. Drop the plugin table from the DB (optional, safe to skip as it only holds AI Link data):

   ```
   docker exec ctfd-db-1 mariadb -uctfd -pctfd ctfd -e "DROP TABLE IF EXISTS ai_links;"
   ```

2. Remove the plugin folder:

   ```
   docker exec ctfd-ctfd-1 rm -rf /opt/CTFd/CTFd/plugins/ai_submissions
   ```

3. Restart CTFd:

   ```
   docker-compose restart ctfd
   ```

4. (Optional) If you ever set a `CTFd` class override, the plugin only applies while the folder exists. Removing the folder and restarting restores original behavior.

---

## License

Open source under the **MIT** license. Free to use, modify, and redistribute. See [LICENSE](LICENSE).
