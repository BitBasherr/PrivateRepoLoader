# Private Repo Loader for Home-Assistant

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
