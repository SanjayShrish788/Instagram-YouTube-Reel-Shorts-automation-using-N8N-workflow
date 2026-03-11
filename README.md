# Bible Shorts Automation

Automated Bible Shorts pipeline that generates vertical videos and publishes them through n8n workflows.

## Overview
This repository contains a two-workflow automation setup:

1. Creator workflow
   1. Selects random Bible verses with no-repeat tracking.
   2. Calls render service to generate shorts.
   3. Uploads generated videos into Google Drive queue.

2. Publisher workflow
   1. Reads queued videos from Google Drive.
   2. Sorts videos in numeric order (`video_1`, `video_2`, ...).
   3. Publishes in controlled batches.
   4. Moves published files to the posted folder.

## How It Works
### 1. Creator Pipeline
1. `Count Queue Files` scans queue and posted folders.
2. `Normalize Count` extracts used verse IDs from filenames.
3. `Pick Bible Reference` builds random chapter candidates.
4. `Fetch Verse` pulls verses from Bible API.
5. `Build Render Payload` prepares render inputs and output filenames.
6. `Render Vertical Video` generates short videos.
7. `Upload to Drive Queue` places files in queue folder.

### 2. Publisher Pipeline
1. `Get Next Queue Video` reads all queue files.
2. `Sort Queue Videos` orders by numeric suffix (`video_<n>`).
3. `Take First Queue Video` selects the current batch size.
4. `Download Queue Video` pulls binaries.
5. Instagram mode:
   1. Upload to Cloudinary.
   2. Create IG media container.
   3. Wait for processing.
   4. Publish IG media.
6. `Move to Posted Folder` archives successfully published files.

## Workflow Screenshots
Add your screenshots into `docs/images` and keep these names:

1. Creator workflow: `docs/images/creator-workflow.png`
2. Publisher workflow: `docs/images/publisher-workflow.png`
3. Google Drive queue: `docs/images/google-drive-queue.png`
4. Google Drive posted: `docs/images/google-drive-posted.png`

Then these will render on GitHub:

![Creator Workflow](docs/images/creator-workflow.png)
![Publisher Workflow](docs/images/publisher-workflow.png)
![Google Drive Queue](docs/images/google-drive-queue.png)
![Google Drive Posted](docs/images/google-drive-posted.png)

## Local Run
1. Copy env file:

```bash
cp .env.local.example .env
```

PowerShell:

```powershell
Copy-Item .env.local.example .env
```

2. Fill required env vars in `.env`.
3. Start services:

```bash
docker compose up -d --build
```

4. Open:
1. n8n: `http://localhost:5678`
2. render API health: `http://localhost:10000/health`

## Deployment Notes
1. `render.yaml` defines cloud services.
2. Do not commit `.env` or local runtime data.
3. Import workflows from:
   1. `n8n/workflows/creator.json`
   2. `n8n/workflows/publisher.json`

## Repository Structure
```text
.
├── .env.example
├── .env.local.example
├── .gitignore
├── docker-compose.yml
├── docs/
│   └── images/
├── n8n/
│   ├── Dockerfile
│   └── workflows/
│       ├── creator.json
│       └── publisher.json
├── render-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── start.sh
│   ├── app/
│   └── scripts/
└── render.yaml
```
