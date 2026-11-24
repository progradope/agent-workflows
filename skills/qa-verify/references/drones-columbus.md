# drones_columbus notes for qa-verify

Main checkout on the Mac: `/Users/shivam/Desktop/drones_columbus`
VPS: reachable from the Mac as the SSH alias `skytrade-vps`. Coding agents run
there in T3 worktrees under `/root/.t3/worktrees/drones/`.

## Which target

Prefer **mac** when the change touches `camera-app/`, or a matrix row needs real
behaviour from the camera stack: live cameras, Frigate detections or
snapshots, incidents created by the orchestrator, go2rtc streams, or the VLM
gateway. Use **vps** for everything else, including UI fixes that seeded data
or the repo's existing test stubs can drive.

## VPS target

- One verification at a time: the machine has about 4 GB of RAM. Check
  `free -h` and `docker ps` before starting anything heavy.
- The camera stack does not run here. Use the repo's existing stubs or test
  profiles for camera services. If a row truly needs the real stack, mark it
  for the mac target instead of faking a result.
- `MAPBOX_TOKEN` comes from the provider environment. If it is missing and a
  test needs it, report that; never let the test skip silently.

## Mac target

Run only in a thread on the Mac environment (or a linked Mac thread).

### Get the code without pushing to GitHub

The branch lives on the VPS. Fetch it over SSH into a separate worktree;
never switch the branch of the main checkout, which the user may be using.

```bash
cd /Users/shivam/Desktop/drones_columbus
git fetch vps "<branch>"
git worktree add ~/qa-worktrees/drones/<task-slug> FETCH_HEAD
```

Confirm the worktree's `git rev-parse HEAD` equals the head SHA you were given.
If the `vps` remote is missing, stop and tell the user to finish the one-time
Mac setup.

### Start the stack, in this order

Record what was already running before you start anything (`docker ps`), and
reuse running services instead of starting duplicates.

1. **Docker:** `docker info`. If it fails, start OrbStack (`open -a OrbStack`)
   and wait until `docker info` succeeds.
2. **Camera stack** (only when the matrix needs it):
   - If the `camera-stack-*`, `go2rtc` and `frigate-worker-01-*` containers are
     already up, reuse them.
   - If they exist but are stopped:
     ```bash
     docker start camera-stack-postgres-1 camera-stack-redis-1 camera-stack-mosquitto-1 \
       camera-stack-vlm-gateway-1 camera-stack-audit-1 go2rtc camera-stack-orchestrator-1 \
       frigate-worker-01-frigate-1 frigate-worker-01-frigate-worker-agent-1
     ```
   - If they do not exist, from `camera-app` in the main checkout: remove
     `deploy/frigate-workers.local.yml` only if it is a stale **directory**
     (never if it is a file), then run `./scripts/stack-up.sh`.
   - If the change modifies `camera-app/` code, the stack must run the changed
     code. Ask the user before stopping or rebuilding a camera stack that was
     already running.
3. **Columbus DB:** `make db-up` (reuse it if it is already running).
4. **user-app**, from the task worktree, in one shell:
   ```bash
   set -a && source /Users/shivam/Desktop/drones_columbus/.env && set +a
   ./mvnw spring-boot:run -pl user-app -am -DskipTests
   ```
   Worktrees do not contain the gitignored `.env`; always load it from the main
   checkout. Never print `.env` values or put them in evidence. If the user's
   own app already holds the port, ask before stopping it, or run on another
   port with `-Dspring-boot.run.arguments=--server.port=<free port>`.

### Finish

- Write the evidence packet and its screenshots in the task worktree's parent
  folder (`~/qa-worktrees/drones/<task-slug>-evidence/`), not inside the repo.
- If you were given a VPS evidence path, copy the packet and artefacts there:
  `scp -r <evidence dir>/. skytrade-vps:<vps evidence path>/`
- Stop only what you started. Leave services that were already running.
- Keep the worktree until the user signs off, then remove it with
  `git worktree remove`.

## Handing a task from the VPS to the Mac

When the VPS thread decides the mac target is needed:

1. Commit the work on the task branch locally (do not push to GitHub).
2. If T3 linked environments are enabled, start a thread on the user's Mac
   environment with the prompt below and wait for its result.
3. Otherwise, stop and give the user this prompt to paste into a new T3 thread
   on the Mac environment, project drones, filled in:

   > Use qa-verify with target mac. Branch `<branch>` at `<full head sha>` from
   > the `vps` remote, for issue `<issue url>`. Verify this matrix: `<rows>`.
   > Copy the evidence to `skytrade-vps:<vps evidence path>` when done.

4. When the evidence arrives, read it and continue to the output review card.
