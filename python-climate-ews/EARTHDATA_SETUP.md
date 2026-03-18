# Earthdata Setup (Satellite Data: GPM IMERG)

GPM IMERG is hosted by NASA GES DISC and usually requires an Earthdata account + authorization.

## 1) Create / Sign in to Earthdata
- Create an account at: https://urs.earthdata.nasa.gov/

## 2) Authorize GES DISC applications
Your account must be approved for GES DISC data access for OPeNDAP/HTTPS downloads.

If you see `401/403` errors during sync, it usually means you need to approve access in your Earthdata profile for the relevant data provider (GES DISC).

## 3) Create credentials for the app
You can use either:
- **Token (recommended):** set `EARTHDATA_TOKEN` in `python-climate-ews\.env`
- **Username/password:** set `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in `python-climate-ews\.env`

Example:
```env
EARTHDATA_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
```

## 4) Run the sync
In the Admin panel:
- `http://localhost:5000/admin/data.html`
- Use **Sync Satellite Rainfall (GPM IMERG)**.

The app will:
- discover the correct daily IMERG files via NASA CMR
- pull point rainfall for each province (lat/lon) via OPeNDAP
- store results in `weather_data` as `source="gpm_imerg"`

## Notes
- IMERG values are stored as **rainfall** only (other variables remain null for these rows).
- Sync runs are logged via `GET /api/admin/sources/sync-runs`.

