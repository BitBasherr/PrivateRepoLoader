# Private Repo Loader for Home-Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Keep **any number** of private GitHub integrations in sync without
exposing their source.

* Stores one **fine-grained PAT** (contents:read-only).
* UI lets you add <repo URL> → <slug> pairs.
* Clones / pulls every 6 h (or on demand via service `private_repo_loader.sync_now`).
* After cloning, HACS sees each folder under `custom_components/` as a
  *manually installed* integration – so changelogs & updates appear
  like normal.

> **Example entry**  
> `url: https://github.com/your-org/awesome_private_component`  
> `slug: awesome_private_component`

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/BitBasherr/PrivateRepoLoader`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Private Repo Loader" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/private_repo_loader` folder
2. Copy it to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Quick Start

1. In Home Assistant, go to **Settings → Devices & Services → + Add Integration**  
   Search **Private Repo Loader**, click it.

2. **Enter your GitHub PAT** (read‐only `repo` scope) or leave blank to enter per-repo later.

3. Click **Configure** on the newly created card, then choose **Add a new repository**:
   - **Repository URL:** `https://github.com/owner/repo`  
   - **Slug:** folder name under `custom_components` (e.g. `my_component`)  
   - **Branch:** (default `main`)  
   - **Token:** (leave blank to use default)

4. Hit **Submit**. The integration will clone/pull, reload HACS, and schedule auto-sync every 6 h.

5. You can trigger immediately via **Developer Tools → Services → `private_repo_loader.sync_now`.**

Your sync progress is exposed in the sensor `sensor.private_repo_loader_last_sync`.

## Requirements

- Home Assistant 2024.6.0 or later
- A GitHub Personal Access Token with `repo` scope for private repositories

## Support

If you encounter any issues, please [open an issue](https://github.com/BitBasherr/PrivateRepoLoader/issues) on GitHub.