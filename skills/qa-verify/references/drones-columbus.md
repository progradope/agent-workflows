# drones_columbus notes for qa-verify

Main checkout on the Mac: `/Users/shivam/Desktop/drones_columbus`

Agent machines (run `hostname` to see which one you are on, then follow its
section below):

| Host | Mac SSH alias | Mac git remote | Repo on the host |
|---|---|---|---|
| `ubuntu-4gb-hel1-2` (Hetzner VPS) | `skytrade-vps` | `vps` | `/mnt/data/drones` |
| `mz-03` (16 GB VM, over Cloudflare) | `mz-ai` | `mz` | `/home/mz/src/drones_columbus` |

The "vps" target means the agent machine the thread runs on. A ticket stays on
the machine where it started.

## Which target

Prefer **mac** when the change touches `camera-app/`, or a matrix row needs real
behaviour from the camera stack: live cameras, Frigate detections or
snapshots, incidents created by the orchestrator, go2rtc streams, or the VLM
gateway. Use **vps** for everything else, including UI fixes that seeded data
or the repo's existing test stubs can drive.

## mz-03

Machine: 4 CPUs, Hyper-V dynamic memory (shows about 1.7 GiB at idle and grows
to about 12 GiB under load), 8 GiB swap file plus 2 GiB swap, 195 GB disk.
Java 21, Docker, the Maven wrapper and Playwright Chromium are installed.
`MAVEN_OPTS=-Xmx3g` is set in `~/.profile` and `~/.mavenrc`.

- **Check the T3 agent memory cap before every heavy step.** T3 caps
  `app-t3code-agents.slice` from the memory visible at idle, which starves
  builds (startup of 11 to 21 minutes, swap thrashing). Check with
  `systemctl --user show app-t3code-agents.slice -p MemoryHigh -p MemoryMax`.
  If MemoryHigh is below 8G, re-apply the approved runtime override:
  `systemctl --user set-property --runtime app-t3code-agents.slice MemoryHigh=12G MemoryMax=14G`,
  confirm it, and record that you did so in the evidence. Never make it
  permanent.
- **Expected times with the cap lifted:** app startup under 70 s; one e2e class
  2.5 to 3.5 minutes; the first run in a fresh worktree builds the Vaadin dev
  bundle (about 30 s) and later runs reuse `target/dev-bundle`. If a run is much
  slower, check the cap first.
- **Parallel work:** one e2e run peaks at about 4 to 6 GiB. Up to two heavy
  verifications may run at the same time; check `free -h` and the cap first.
- MAPBOX_TOKEN, Testcontainers clean-up, Playwright install and the camera
  stack: same rules as the VPS below.

## VPS (ubuntu-4gb-hel1-2)

Machine: 2 CPUs, 3.7 GiB RAM, 8 GiB swap. Java 21, Docker, the Maven wrapper,
and Playwright 1.49 with Chromium are installed.

- **One heavy step at a time.** Check `free -h` and `docker ps` first. Run Maven
  with `MAVEN_OPTS=-Xmx1200m` and under `nice`. Build only what you need
  (`-pl user-app -am`); a cold full `test-compile` takes about 11 minutes,
  mostly frontend/node builds.
- **E2E command:**
  `./mvnw test -Pe2e -pl user-app -am -De2e.headless=true -Dtest=<Class> -B`.
  Expect 3 to 5 minutes per test class.
- **Cold start in a fresh worktree:** the first e2e run builds Vaadin's dev
  bundle during app startup, and the login form can miss its 20 s wait. Before
  treating an e2e failure as real, warm up with `LoginEnumerationE2ETest` or
  rerun once, and record both runs in the evidence.
- **MAPBOX_TOKEN** comes from the provider environment. Tests that call
  `assumeMapboxTokenConfigured()` are skipped, not failed, when it is unset
  (the Adsb*, Airspace*, Detection*, Tfr* and several permit/operation e2e
  classes). A skipped test is not a pass: report skipped tests by name. Other
  tests that geocode municipalities through Mapbox may fail without it.
- **Testcontainers clean-up:** after your runs, check `docker ps` for
  containers your session left (label `org.testcontainers.sessionId`) and
  remove them. If removal is denied, report the container IDs to the user.
- **Playwright browsers:** if Chromium is missing, run
  `com.microsoft.playwright.CLI install --with-deps chromium` with `java -cp`
  on the Playwright jars in `~/.m2`. `exec:java` under `-pl user-app -am` fails
  because `common` has no Playwright dependency.
- The camera stack does not run here. Use the repo's existing stubs or test
  profiles for camera services. If a row truly needs the real stack, mark it
  for the mac target instead of faking a result.

## Mac target

Run only in a thread on the Mac environment (or a linked Mac thread).

### Get the code without pushing to GitHub

The branch lives on the agent machine. Fetch it over SSH from that machine's
remote (`vps` or `mz`, see the table at the top) into a separate worktree;
never switch the branch of the main checkout, which the user may be using.
`mz` is reachable only while the Cloudflare One client on the Mac is
connected.

```bash
cd /Users/shivam/Desktop/drones_columbus
git fetch <remote> "<branch>"
git worktree add ~/qa-worktrees/drones/<task-slug> FETCH_HEAD
```

Confirm the worktree's `git rev-parse HEAD` equals the head SHA you were given.
If the remote is missing, stop and tell the user to finish the one-time Mac
setup.

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
- If you were given an evidence path on the agent machine, copy the packet and
  artefacts there with that machine's alias:
  `scp -r <evidence dir>/. <alias>:<evidence path>/`
- Stop only what you started. Leave services that were already running.
- Keep the worktree until the user signs off, then remove it with
  `git worktree remove`.

## Handing a task from an agent machine to the Mac

When an agent-machine thread decides the mac target is needed:

1. Commit the work on the task branch locally (do not push to GitHub).
2. If T3 linked environments are enabled, start a thread on the user's Mac
   environment with the prompt below and wait for its result.
3. Otherwise, stop and give the user this prompt to paste into a new T3 thread
   on the Mac environment, project drones, filled in:

   > Use qa-verify with target mac. Branch `<branch>` at `<full head sha>` from
   > the `<vps or mz>` remote, for issue `<issue url>`. Verify this matrix:
   > `<rows>`. Copy the evidence to `<skytrade-vps or mz-ai>:<evidence path>`
   > when done.

4. When the evidence arrives, read it and continue to the output review card.
